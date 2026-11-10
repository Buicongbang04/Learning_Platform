import json
import re
import uuid

import pytest
import requests
import yaml

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
AUTH = ("admin", "admin")
PANEL_TYPES = {"timeseries", "stat", "table", "gauge", "bargauge", "histogram", "barchart", "heatmap"}
DS_REF = {"type": "prometheus", "uid": "${datasource}"}


@pytest.fixture(scope="module")
def dashboard():
    return json.loads(ex.read("dashboard.json"))


@pytest.fixture(scope="module")
def provider():
    return yaml.safe_load(ex.read("provider.yml"))


@pytest.fixture(scope="module")
def grafana():
    mlopskit.require_stack("grafana", "prometheus")
    return f"http://127.0.0.1:{mlopskit.stack_port('grafana')}"


def exprs(dashboard):
    return [(p, t["expr"]) for p in dashboard["panels"] for t in p.get("targets", [])]


def panel_for(dashboard, *needles):
    return [p for p, expr in exprs(dashboard) if all(n in expr for n in needles)]


def test_dashboard_metadata(dashboard):
    assert dashboard["title"].strip()
    assert {"mlops", "eta"} <= set(dashboard.get("tags", []))
    assert isinstance(dashboard["schemaVersion"], int) and dashboard["schemaVersion"] >= 39
    assert dashboard["time"]["from"] == "now-6h"
    assert dashboard["refresh"] in ("30s", "1m")
    assert dashboard.get("id") is None
    assert 0 < len(str(dashboard.get("uid", "x"))) <= 40


def test_datasource_is_a_variable(dashboard):
    variables = {v["name"]: v for v in dashboard["templating"]["list"]}
    assert variables["datasource"]["type"] == "datasource"
    assert variables["datasource"]["query"] == "prometheus"
    assert len(dashboard["panels"]) >= 6
    for panel in dashboard["panels"]:
        assert panel["datasource"] == DS_REF, panel.get("title")
        for target in panel["targets"]:
            assert target["datasource"] == DS_REF, panel.get("title")


def test_panels_are_well_formed(dashboard):
    assert dashboard["panels"]
    ids = [p["id"] for p in dashboard["panels"]]
    assert len(ids) == len(set(ids))
    boxes = []
    for panel in dashboard["panels"]:
        assert panel["title"].strip()
        assert panel["type"] in PANEL_TYPES
        pos = panel["gridPos"]
        assert 0 <= pos["x"] and pos["x"] + pos["w"] <= 24 and pos["w"] >= 3 and pos["h"] >= 3
        boxes.append((pos["x"], pos["y"], pos["x"] + pos["w"], pos["y"] + pos["h"]))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], f"hai panel chồng lên nhau: {a} {b}"


def test_required_panels_use_the_right_metrics(dashboard):
    assert panel_for(dashboard, "http_requests_total", "rate(")
    errors = panel_for(dashboard, "http_requests_total", 'status=~"5')
    assert errors and all("/" in e["targets"][0]["expr"] for e in errors)
    latency = [p for p, expr in exprs(dashboard)
               if "histogram_quantile(0.95" in expr and "http_request_duration_seconds_bucket" in expr
               and re.search(r"\bby\s*\([^)]*\ble\b", expr)]
    assert latency
    version = panel_for(dashboard, "eta_model_info")
    assert version and version[0]["type"] in ("stat", "table")
    assert panel_for(dashboard, "eta_prediction_seconds_bucket", "histogram_quantile")
    assert panel_for(dashboard, "eta_fallback_total", "rate(")


def test_counters_are_never_plotted_raw(dashboard):
    assert exprs(dashboard)
    for panel, expr in exprs(dashboard):
        if "_total" in expr:
            assert re.search(r"\b(rate|increase)\(", expr), f"{panel['title']}: counter phải qua rate() hoặc increase()"


def test_only_known_macros_are_used(dashboard):
    assert exprs(dashboard)
    for panel, expr in exprs(dashboard):
        assert set(re.findall(r"\$\{?(\w+)", expr)) <= {"__rate_interval"}, f"{panel['title']}: chỉ dùng $__rate_interval"


def test_provider_file(provider):
    assert provider["apiVersion"] == 1
    assert len(provider["providers"]) == 1
    entry = provider["providers"][0]
    assert entry["type"] == "file"
    assert str(entry["folder"]).strip()
    assert entry["disableDeletion"] is True
    assert entry["allowUiUpdates"] is False
    assert entry["updateIntervalSeconds"] >= 10
    assert entry["options"]["path"].startswith("/var/lib/grafana/dashboards")


def test_grafana_accepts_the_dashboard_and_every_query_parses(grafana, dashboard):
    assert exprs(dashboard)
    uid = f"ex-{uuid.uuid4().hex[:12]}"
    body = dict(dashboard, uid=uid, title=f"{dashboard['title']} [{uid}]", id=None)
    try:
        saved = requests.post(f"{grafana}/api/dashboards/db", auth=AUTH, timeout=20,
                              json={"dashboard": body, "overwrite": False, "message": "mlops-ex"})
        assert saved.status_code == 200, saved.text
        fetched = requests.get(f"{grafana}/api/dashboards/uid/{uid}", auth=AUTH, timeout=20)
        assert fetched.status_code == 200
        stored = fetched.json()["dashboard"]
        assert [p["title"] for p in stored["panels"]] == [p["title"] for p in dashboard["panels"]]
        datasource = requests.get(f"{grafana}/api/datasources/name/Prometheus", auth=AUTH, timeout=20)
        assert datasource.status_code == 200
        ds = {"type": "prometheus", "uid": datasource.json()["uid"]}
        for panel, expr in exprs(stored):
            query = {"queries": [{"refId": "A", "datasource": ds, "expr": expr, "instant": True, "range": False,
                                  "intervalMs": 15000, "maxDataPoints": 100}], "from": "now-1h", "to": "now"}
            reply = requests.post(f"{grafana}/api/ds/query", auth=AUTH, json=query, timeout=30)
            assert reply.status_code == 200, f"{panel['title']}: {reply.text[:300]}"
            assert "error" not in reply.json()["results"]["A"], f"{panel['title']}: {reply.text[:300]}"
    finally:
        requests.delete(f"{grafana}/api/dashboards/uid/{uid}", auth=AUTH, timeout=20)
    assert requests.get(f"{grafana}/api/dashboards/uid/{uid}", auth=AUTH, timeout=20).status_code == 404
