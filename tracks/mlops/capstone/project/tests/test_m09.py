"""M09: metric Prometheus của API, alert rule có test promtool, dashboard Grafana as code. Đề ở capstone/milestones/m09-monitoring.md."""

import json
import re
import uuid
from contextlib import contextmanager

import joblib
import pytest
import requests
import yaml
from etakit import need, require_file

import mlopskit

TRIP = {"PULocationID": 161, "DOLocationID": 236, "pickup_datetime": "2019-01-15T08:30:00", "trip_distance": 2.4}
ALERTS = ["EtaHighErrorRate", "EtaHighLatencyP95", "EtaMetricsAbsent", "EtaPredictionShift"]
ALLOWED_LABELS = {"status", "variant", "version", "le"}
BASE = 'job="eta-api",instance="api:8000"'
DURATION = re.compile(r"^(\d+)([smhd])$")
AUTH = ("admin", "admin")


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("m09")


@contextmanager
def started_api(monkeypatch, model_dir, trips):
    """Khởi động app trong test (không ở setup fixture) để thiếu code thì test fail kèm thông báo thay vì ERROR."""
    from fastapi.testclient import TestClient

    path = model_dir / "champion.joblib"
    if not path.is_file():
        features = need("features", "build_features")
        train = need("train", "train")
        joblib.dump(train.train(*features.build_features(trips), {"max_iter": 20, "random_state": 0}), path)
    for key in ("ETA_CHALLENGER_PATH", "ETA_CANARY_WEIGHT", "ETA_SHADOW", "ETA_ADMIN_TOKEN", "ETA_SPEED_TABLE", "ETA_PREDICTION_LOG"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ETA_MODEL_PATH", str(path))
    monkeypatch.setenv("ETA_MODEL_VERSION", "m09-v1")
    serve = need("serve", "app")
    with TestClient(serve.app) as client:
        yield client


def scrape(api) -> dict:
    from prometheus_client.parser import text_string_to_metric_families

    reply = api.get("/metrics")
    assert reply.status_code == 200, "cần GET /metrics dạng text Prometheus"
    samples = {}
    for family in text_string_to_metric_families(reply.text):
        for sample in family.samples:
            samples[(sample.name, tuple(sorted(sample.labels.items())))] = sample.value
    return samples


def total(samples: dict, name: str, **labels) -> float:
    return sum(value for (sample, items), value in samples.items()
               if sample == name and all(dict(items).get(k) == v for k, v in labels.items()))


def test_m09_metrics_exposed(project, monkeypatch, model_dir, synthetic_trips):
    with started_api(monkeypatch, model_dir, synthetic_trips) as api:
        check_metrics(api)


def check_metrics(api):
    before = scrape(api)
    for i in range(4):
        assert api.post("/predict", json=TRIP, headers={"X-Request-ID": f"m09-{i}"}).status_code == 200
    assert api.post("/predict", json={**TRIP, "trip_distance": -1}).status_code == 422
    after = scrape(api)

    def delta(name, **labels):
        return total(after, name, **labels) - total(before, name, **labels)

    assert delta("eta_requests_total", status="200") == 4, "eta_requests_total{status=\"200\"} phải tăng đúng 4"
    assert delta("eta_requests_total", status="422") == 1, "request validate lỗi phải được đếm status=\"422\""
    assert delta("eta_requests_total", status="200", variant="champion") == 4, "request do champion trả lời có variant=\"champion\""
    assert delta("eta_request_duration_seconds_count") == 5, "histogram độ trễ đếm mọi request /predict"
    assert total(after, "eta_request_duration_seconds_bucket", le="0.3") > 0, "histogram độ trễ cần bucket le=0.3 (ngưỡng alert)"
    assert delta("eta_prediction_seconds_count") == 4, "histogram giá trị dự đoán đếm mỗi dự đoán thành công"
    assert total(after, "eta_model_info", version="m09-v1", variant="champion") == 1, "eta_model_info{version, variant} = 1"
    assert ("eta_fallback_total", ()) in after, "giữ counter eta_fallback_total của M07"
    for (name, items) in after:
        if name.startswith("eta_"):
            extra = {k for k, _ in items} - ALLOWED_LABELS
            assert not extra, f"{name} có label {extra}: chỉ dùng {sorted(ALLOWED_LABELS)} (cardinality thấp, không request_id)"


def rules_dir(project):
    require_file("monitoring", "prometheus.yml")
    require_file("monitoring", "rules", "eta.rules.yml")
    require_file("monitoring", "rules", "eta.rules.test.yml")
    return project / "monitoring"


def seconds(text) -> int:
    match = DURATION.match(str(text))
    assert match, f"thời lượng không hợp lệ: {text!r}"
    return int(match.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]


def alert_rules(path) -> dict:
    found = {}
    for group in yaml.safe_load(path.read_text(encoding="utf-8"))["groups"]:
        for rule in group.get("rules", []):
            if "alert" in rule:
                found[rule["alert"]] = rule
    return found


def test_m09_rules_promtool(project):
    monitoring = rules_dir(project)
    config = yaml.safe_load((monitoring / "prometheus.yml").read_text(encoding="utf-8"))
    jobs = {job["job_name"] for job in config.get("scrape_configs", [])}
    assert "eta-api" in jobs, "prometheus.yml cần scrape job eta-api"
    result = mlopskit.promtool("check", "config", "prometheus.yml", cwd=monitoring)
    assert result.returncode == 0, result.stdout + result.stderr
    result = mlopskit.promtool("test", "rules", "eta.rules.test.yml", cwd=monitoring / "rules")
    assert result.returncode == 0, result.stdout + result.stderr
    rules = alert_rules(monitoring / "rules" / "eta.rules.yml")
    assert set(ALERTS) <= set(rules), f"cần đủ alert {ALERTS}, có {sorted(rules)}"
    expected_for = {"EtaHighErrorRate": 300, "EtaHighLatencyP95": 600}
    for name in ALERTS:
        rule = rules[name]
        assert seconds(rule.get("for", "0s")) > 0, f"{name}: cần for"
        assert rule.get("labels", {}).get("severity") in ("critical", "warning"), f"{name}: severity critical hoặc warning"
        annotations = rule.get("annotations", {})
        assert str(annotations.get("summary", "")).strip(), f"{name}: cần annotations.summary"
        assert str(annotations.get("runbook_url", "")).startswith("https://") and "runbook" in annotations["runbook_url"], \
            f"{name}: runbook_url https:// trỏ tới runbook"
        if name in expected_for:
            assert seconds(rule["for"]) == expected_for[name], f"{name}: for phải là {expected_for[name] // 60}m"


def scenario(tmp_path, rules_text, series, expectations):
    tmp_path.mkdir()
    (tmp_path / "eta.rules.yml").write_text(rules_text, encoding="utf-8")
    checks = [{"expr": f'count(ALERTS{{alertname="{alert}",alertstate="firing"}})', "eval_time": at,
               "exp_samples": [{"labels": "{}", "value": 1}] if firing else []} for alert, at, firing in expectations]
    spec = {"rule_files": ["eta.rules.yml"], "evaluation_interval": "1m",
            "tests": [{"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in series],
                       "promql_expr_test": checks}]}
    (tmp_path / "grading.test.yml").write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    result = mlopskit.promtool("test", "rules", "grading.test.yml", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def requests_series(ok: str, errors: str, info: str = "1x40"):
    return [
        (f'eta_requests_total{{{BASE},status="200",variant="champion"}}', ok),
        (f'eta_requests_total{{{BASE},status="500",variant="none"}}', errors),
        (f'eta_request_duration_seconds_bucket{{{BASE},variant="champion",le="0.3"}}', ok),
        (f'eta_request_duration_seconds_bucket{{{BASE},variant="champion",le="+Inf"}}', ok),
        (f'eta_model_info{{{BASE},version="3",variant="champion"}}', info),
    ]


def test_m09_rules_no_traffic(project, tmp_path):
    monitoring = rules_dir(project)
    rules_text = (monitoring / "rules" / "eta.rules.yml").read_text(encoding="utf-8")
    scenario(tmp_path / "quiet", rules_text, requests_series("0+0x40", "0+0x40"), [
        ("EtaHighErrorRate", "15m", False), ("EtaHighErrorRate", "30m", False),
        ("EtaHighLatencyP95", "30m", False), ("EtaMetricsAbsent", "30m", False),
    ])
    scenario(tmp_path / "errors", rules_text, requests_series("0+90x40", "0+10x40"), [
        ("EtaHighErrorRate", "2m", False), ("EtaHighErrorRate", "15m", True), ("EtaMetricsAbsent", "15m", False),
    ])
    scenario(tmp_path / "gone", rules_text, requests_series("0+90x10 stale", "0+0x10 stale", "1x10 stale"), [
        ("EtaMetricsAbsent", "3m", False), ("EtaMetricsAbsent", "25m", True), ("EtaHighErrorRate", "25m", False),
    ])
    own = yaml.safe_load((monitoring / "rules" / "eta.rules.test.yml").read_text(encoding="utf-8"))
    quiet_case = absent_case = False
    for case in own.get("tests", []):
        counters = [s["values"] for s in case.get("input_series", []) if str(s["series"]).startswith("eta_requests_total")]
        flat = bool(counters) and all(re.fullmatch(r"\s*0(\+0)?x\d+\s*", str(v)) for v in counters)
        expect = {(t["alertname"], bool(t.get("exp_alerts"))) for t in case.get("alert_rule_test", [])}
        quiet_case |= flat and ("EtaHighErrorRate", False) in expect
        absent_case |= ("EtaMetricsAbsent", True) in expect
    assert quiet_case, "eta.rules.test.yml cần một ca không traffic (mọi eta_requests_total đứng yên ở 0) với EtaHighErrorRate không bắn"
    assert absent_case, "eta.rules.test.yml cần một ca EtaMetricsAbsent bắn"


def test_m09_dashboard_provisioned(project, monkeypatch, model_dir, synthetic_trips):
    path = require_file("monitoring", "grafana", "dashboards", "eta.json")
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    with started_api(monkeypatch, model_dir, synthetic_trips) as api:
        for _ in range(3):
            api.post("/predict", json=TRIP)
        exposed = {name for name, _ in scrape(api)}
    exprs = [(p.get("title", "?"), t["expr"]) for p in dashboard.get("panels", []) for t in p.get("targets", []) if "expr" in t]
    assert exprs, "dashboard chưa có panel nào có truy vấn"
    used = set()
    for title, expr in exprs:
        names = set(re.findall(r"\b(eta_[a-z0-9_]+)", expr))
        unknown = names - exposed
        assert not unknown, f"panel {title!r} dùng metric không có trong /metrics: {sorted(unknown)}"
        used |= names
    required = {"eta_requests_total", "eta_request_duration_seconds_bucket", "eta_prediction_seconds_bucket", "eta_model_info"}
    assert required <= used, f"dashboard cần panel RED, phân phối dự đoán và version: thiếu {sorted(required - used)}"
    mlopskit.require_stack("grafana")
    grafana = f"http://127.0.0.1:{mlopskit.stack_port('grafana')}"
    uid = f"mlops-ex-{uuid.uuid4().hex[:12]}"
    body = dict(dashboard, uid=uid, title=f"{dashboard.get('title', 'ETA')} [{uid}]", id=None)
    try:
        saved = requests.post(f"{grafana}/api/dashboards/db", auth=AUTH, timeout=20,
                              json={"dashboard": body, "overwrite": False, "message": "mlops-ex m09"})
        assert saved.status_code == 200, saved.text
        fetched = requests.get(f"{grafana}/api/dashboards/uid/{uid}", auth=AUTH, timeout=20)
        assert fetched.status_code == 200, fetched.text
        stored = fetched.json()["dashboard"]
        assert [p.get("title") for p in stored["panels"]] == [p.get("title") for p in dashboard["panels"]]
    finally:
        requests.delete(f"{grafana}/api/dashboards/uid/{uid}", auth=AUTH, timeout=20)
    assert requests.get(f"{grafana}/api/dashboards/uid/{uid}", auth=AUTH, timeout=20).status_code == 404
