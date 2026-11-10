import json
import re
import shutil
import time
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import DockerLab, Exercise, ObsStack

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
APP = testkit.ROOT / "tracks" / "devops" / "sample-app"
DASHBOARD = "observability/grafana/dashboards/olist-api.json"
PROVIDER = "observability/grafana/provisioning/dashboards/dashboards.yaml"
UID = "olist-api-red"
FOLDER = "Olist Shop"
DATASOURCES = {"prometheus": "prometheus", "loki": "loki"}
PANEL_TYPES = {"timeseries", "stat", "gauge", "bargauge", "table", "logs", "heatmap"}
WINDOW = re.compile(r"\b(?:rate|increase|irate)\s*\([^\[]*\[([^\]]+)\]")


def dashboard() -> dict:
    try:
        data = json.loads(ex.read(DASHBOARD))
    except json.JSONDecodeError as error:
        pytest.fail(f"{DASHBOARD} không phải JSON hợp lệ: {error}")
    assert isinstance(data, dict), f"{DASHBOARD} phải là một object JSON"
    return data


def provider() -> dict:
    try:
        data = yaml.safe_load(ex.read(PROVIDER))
    except yaml.YAMLError as error:
        pytest.fail(f"{PROVIDER} không phải YAML hợp lệ: {error}")
    assert isinstance(data, dict) and data.get("apiVersion") == 1, f"{PROVIDER} cần apiVersion: 1"
    return data


def panels(data: dict) -> list[dict]:
    found = []
    for panel in data.get("panels") or []:
        found.append(panel)
        found.extend(panel.get("panels") or [])
    return [p for p in found if p.get("type") != "row"]


def targets(data: dict) -> list[tuple[dict, dict]]:
    return [(panel, target) for panel in panels(data) for target in panel.get("targets") or []]


def exprs(data: dict, kind: str) -> list[str]:
    return [str(t.get("expr", "")) for _, t in targets(data) if (t.get("datasource") or {}).get("type") == kind]


def find(data: dict, kind: str, *needles: str) -> list[str]:
    return [e for e in exprs(data, kind) if all(re.search(n, e) for n in needles)]


def test_provider_puts_dashboards_in_folder():
    providers = provider().get("providers") or []
    olist = [p for p in providers if p.get("folder") == FOLDER]
    assert len(olist) == 1, f"Cần đúng một provider có folder: {FOLDER}"
    p = olist[0]
    assert p.get("type") == "file", "Provider phải là type: file"
    assert (p.get("options") or {}).get("path") == "/etc/grafana/dashboards", "options.path phải là /etc/grafana/dashboards"
    assert p.get("allowUiUpdates") is False, "allowUiUpdates: false để dashboard chỉ đổi qua Git"
    assert p.get("disableDeletion") is True, "disableDeletion: true để không ai xoá được dashboard trên UI"
    assert isinstance(p.get("updateIntervalSeconds"), int) and 10 <= p["updateIntervalSeconds"] <= 300, \
        "updateIntervalSeconds từ 10 tới 300"


def test_dashboard_identity():
    data = dashboard()
    assert data.get("uid") == UID, f"uid phải là {UID}"
    assert str(data.get("title", "")).strip() and "TODO" not in data["title"], "Đặt title cho dashboard"
    assert {"olist", "red"} <= set(data.get("tags") or []), "tags cần có olist và red"
    assert isinstance(data.get("schemaVersion"), int) and data["schemaVersion"] >= 39, "schemaVersion từ 39"


def test_panels_use_provisioned_datasources():
    data = dashboard()
    assert len(panels(data)) >= 5, "Cần ít nhất 5 panel"
    for panel in panels(data):
        assert panel.get("type") in PANEL_TYPES, f"Panel '{panel.get('title')}': type {panel.get('type')} không thuộc {sorted(PANEL_TYPES)}"
        assert panel.get("targets"), f"Panel '{panel.get('title')}' không có query"
        grid = panel.get("gridPos") or {}
        assert all(isinstance(grid.get(k), int) for k in "xywh") and grid["x"] + grid["w"] <= 24, \
            f"Panel '{panel.get('title')}': gridPos cần x, y, w, h và nằm trong 24 cột"
    for panel, target in targets(data):
        source = target.get("datasource") or panel.get("datasource") or {}
        assert DATASOURCES.get(source.get("type")) == source.get("uid"), (
            f"Panel '{panel.get('title')}': datasource phải là {{type, uid}} của datasource đã provision "
            f"(prometheus/prometheus hoặc loki/loki), đang là {source}")


def test_red_queries_present():
    data = dashboard()
    missing = []
    if not find(data, "prometheus", r"\brate\(", r"http_requests_total"):
        missing.append("Rate: rate(http_requests_total ...)")
    if not find(data, "prometheus", r"http_requests_total", r"5\.\.", r"/"):
        missing.append("Errors: tỉ lệ 5xx (phép chia, lọc mã 5..)")
    if not find(data, "prometheus", r"histogram_quantile\(\s*0?\.95", r"http_request_duration_seconds_bucket", r"\ble\b"):
        missing.append("Duration: histogram_quantile(0.95, ... le ...)")
    if not find(data, "prometheus", r"\brate\(", r"jobs_processed_total"):
        missing.append("Worker: rate(jobs_processed_total ...)")
    logs = [p for p in panels(data) if p.get("type") == "logs"]
    if not logs or not find(data, "loki", r'service_name="olist-shop-api"'):
        missing.append('Panel logs với query Loki trên {service_name="olist-shop-api"}')
    assert not missing, "Còn thiếu: " + "; ".join(missing)


def test_counters_and_windows():
    data = dashboard()
    for expr in exprs(data, "prometheus"):
        bare = re.sub(r"\b(?:rate|increase|irate)\s*\([^()]*\)", "", expr)
        assert not re.search(r"\w+_total\b", bare), f"Counter vẽ thô, cần rate()/increase(): {expr}"
        windows = WINDOW.findall(expr)
        assert all(w == "$__rate_interval" for w in windows), f"Cửa sổ của rate() trong dashboard dùng $__rate_interval: {expr}"


def olist_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(APP / "olist_shop", project / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(APP / "requirements.txt", project)
    shutil.copy(testkit.KUBE_OLIST_DOCKERFILE, project / "Dockerfile")
    shutil.copy(FIXTURES / "compose.yaml", project / "compose.yaml")
    shutil.copytree(ex.path("observability"), project / "observability")
    return project


def send_traffic(stack: ObsStack) -> None:
    import httpx

    api = f"http://127.0.0.1:{stack.project.port('api', 8000)}"
    with httpx.Client(trust_env=False, timeout=10) as client:
        for round in range(2):
            assert client.post(f"{api}/jobs/recompute").status_code == 202
            for i in range(10):
                client.get(f"{api}/orders/b02-{round}-{i}")
            client.get(f"{api}/stats/revenue-by-state")
            done = stack.prom_query(f'jobs_processed_total{{job="olist-worker"}} >= {round + 1}', timeout=60)
            assert done, "Worker chưa xử lý job"
        stopped = stack.project.run("stop", "redis")
        assert stopped.returncode == 0, stopped.stderr
        for round in range(2):
            for _ in range(3):
                assert client.get(f"{api}/readyz").status_code == 503
            assert stack.prom_query(f'http_requests_total{{job="olist-api", status="503"}} >= {3 * (round + 1)}', timeout=30)


def grafana_query(stack: ObsStack, panel: dict, target: dict) -> int:
    import httpx

    source = target.get("datasource") or panel.get("datasource")
    query = {**target, "datasource": source, "refId": target.get("refId", "A"), "intervalMs": 15000, "maxDataPoints": 200}
    if source.get("type") == "loki":
        query.setdefault("queryType", "range")
        query.setdefault("maxLines", 100)
    now = int(time.time() * 1000)
    body = {"from": str(now - 15 * 60 * 1000), "to": str(now), "queries": [query]}
    with httpx.Client(trust_env=False, timeout=30) as client:
        response = client.post(stack.url("grafana") + "/api/ds/query", json=body)
    result = response.json().get("results", {}).get(query["refId"], {})
    if response.status_code >= 400 or result.get("error"):
        pytest.fail(f"Panel '{panel.get('title')}': Grafana trả lỗi cho `{target.get('expr')}`: {result.get('error') or response.text[:500]}")
    values = [v for frame in result.get("frames") or [] for column in frame.get("data", {}).get("values", [])[1:]
              for v in column if v is not None]
    return len(values)


def test_dashboard_provisioned_and_panels_return_data(tmp_path):
    data = dashboard()
    assert data.get("uid") == UID and len(panels(data)) >= 5, "Hoàn thiện dashboard trước (xem các test tĩnh)"
    for image in (testkit.KUBE_IMAGES["postgres"], testkit.KUBE_IMAGES["redis"], "python:3.12.16-slim-trixie"):
        ex.require_image(image)
    project = olist_project(tmp_path)
    with DockerLab() as lab:
        stack = ObsStack(lab, project=project)
        found = [d for d in stack.grafana_dashboards() if d.get("uid") == UID]
        assert found, f"Grafana không nạp dashboard uid {UID}. Log Grafana:\n{stack.project.logs('grafana', tail=30)[-3000:]}"
        assert found[0].get("folderTitle") == FOLDER, f"Dashboard nằm trong folder '{found[0].get('folderTitle')}', cần '{FOLDER}'"
        loaded = stack.grafana_dashboard(UID)
        assert len(panels(loaded)) == len(panels(data)), "Grafana nạp số panel khác với tệp"
        send_traffic(stack)
        empty = []
        for panel, target in targets(loaded):
            if not stack.eventually(lambda: grafana_query(stack, panel, target), 45, 3):
                empty.append(f"'{panel.get('title')}': {target.get('expr')}")
        assert not empty, "Query không trả dữ liệu dù Olist Shop đã có traffic, job và lỗi 503:\n" + "\n".join(empty)
