import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import DockerLab, Exercise, ObsStack

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
APP = testkit.ROOT / "tracks" / "devops" / "sample-app"
CONFIG = "observability/otel-collector/config.yaml"
ENV_KEY = "deployment.environment.name"


def config() -> dict:
    try:
        data = yaml.safe_load(ex.read(CONFIG))
    except yaml.YAMLError as error:
        pytest.fail(f"{CONFIG} không phải YAML hợp lệ: {error}")
    assert isinstance(data, dict), f"{CONFIG} phải là một mapping"
    return data


def kind(name: str) -> str:
    return str(name).split("/")[0]


def pipeline(data: dict, signal: str) -> dict:
    pipelines = (data.get("service") or {}).get("pipelines") or {}
    return pipelines.get(signal) or {}


def test_traces_pipeline_shape():
    data = config()
    traces = pipeline(data, "traces")
    assert "otlp" in [kind(r) for r in traces.get("receivers") or []], "Pipeline traces phải nhận từ receiver otlp"
    processors = traces.get("processors") or []
    assert processors and kind(processors[0]) == "memory_limiter", "memory_limiter phải đứng đầu danh sách processor"
    assert kind(processors[-1]) == "batch", "batch phải đứng cuối danh sách processor"
    resource = [p for p in processors if kind(p) == "resource"]
    assert resource, "Pipeline traces cần một processor resource"
    attributes = ((data.get("processors") or {}).get(resource[0]) or {}).get("attributes") or []
    assert any(a.get("key") == ENV_KEY and a.get("value") == "lab" and a.get("action") in ("upsert", "insert") for a in attributes), \
        f"Processor {resource[0]} cần gắn {ENV_KEY}=lab (action upsert hoặc insert)"
    exporters = traces.get("exporters") or []
    jaeger = [e for e in exporters if kind(e) == "otlp" and "jaeger" in str(((data.get("exporters") or {}).get(e) or {}).get("endpoint", ""))]
    assert jaeger, "Pipeline traces cần một exporter otlp trỏ tới jaeger:4317"
    assert "spanmetrics" in [kind(e) for e in exporters], "Pipeline traces cần xuất sang connector spanmetrics"


def test_metrics_and_logs_pipelines_shape():
    data = config()
    metrics = pipeline(data, "metrics")
    assert "spanmetrics" in [kind(r) for r in metrics.get("receivers") or []], "Pipeline metrics phải nhận từ spanmetrics"
    exporters = data.get("exporters") or {}
    prom = [e for e in metrics.get("exporters") or [] if kind(e) == "prometheus"]
    assert prom and str((exporters.get(prom[0]) or {}).get("endpoint", "")).endswith(":8889"), \
        "Pipeline metrics cần exporter prometheus ở cổng 8889 (Prometheus của stack scrape otel-collector:8889)"
    connector = ((data.get("connectors") or {}).get("spanmetrics")) or {}
    dims = [d.get("name") for d in connector.get("dimensions") or []]
    assert "http.response.status_code" in dims, "spanmetrics cần dimension http.response.status_code"
    flush = str(connector.get("metrics_flush_interval", "60s"))
    assert flush.endswith("s") and not flush.endswith("ms") and float(flush[:-1]) <= 15, "metrics_flush_interval tối đa 15s"
    logs = pipeline(data, "logs")
    assert "otlphttp/loki" in (logs.get("exporters") or []), "Giữ pipeline logs gửi tới otlphttp/loki"


def olist_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(APP / "olist_shop", project / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(APP / "requirements.txt", project)
    shutil.copy(testkit.KUBE_OLIST_DOCKERFILE, project / "Dockerfile")
    shutil.copy(FIXTURES / "compose.yaml", project / "compose.yaml")
    folder = project / "observability" / "otel-collector"
    folder.mkdir(parents=True)
    shutil.copy(ex.path(CONFIG), folder / "config.yaml")
    return project


def raw_traces(stack: ObsStack, service: str) -> list[dict]:
    import httpx

    now = datetime.now(timezone.utc)
    params = {"query.service_name": service, "query.search_depth": "20",
              "query.start_time_min": (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
              "query.start_time_max": (now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")}
    with httpx.Client(trust_env=False, timeout=10) as client:
        response = client.get(stack.url("jaeger") + "/api/v3/traces", params=params)
    if response.status_code == 404:
        return []
    return (response.json().get("result") or {}).get("resourceSpans") or []


def resource_env(stack: ObsStack, service: str) -> set:
    values = set()
    for resource in raw_traces(stack, service):
        attrs = {a["key"]: a.get("value", {}).get("stringValue") for a in resource.get("resource", {}).get("attributes", [])}
        values.add(attrs.get(ENV_KEY))
    return values


def test_pipeline_end_to_end(tmp_path):
    test_traces_pipeline_shape()
    test_metrics_and_logs_pipelines_shape()
    for image in (testkit.KUBE_IMAGES["postgres"], testkit.KUBE_IMAGES["redis"], "python:3.12.16-slim-trixie"):
        ex.require_image(image)
    import httpx

    with DockerLab() as lab:
        stack = ObsStack(lab, project=olist_project(tmp_path))
        api = f"http://127.0.0.1:{stack.project.port('api', 8000)}"
        with httpx.Client(trust_env=False, timeout=10) as client:
            for i in range(3):
                assert client.get(f"{api}/orders/i01-{i}", headers={"X-Request-ID": f"i01-{i}"}).status_code == 404
            assert client.post(f"{api}/jobs/recompute", headers={"X-Request-ID": "i01-job"}).status_code == 202

        def order_traces():
            return [t for t in stack.jaeger_traces("olist-shop-api") if any(s["name"] == "GET /orders/{order_id}" for s in t["spans"])]

        traces = stack.eventually(order_traces, 60)
        assert traces, "Jaeger không có trace GET /orders/{order_id}: trace chưa tới Jaeger"
        spans = traces[0]["spans"]
        server = next(s for s in spans if s["name"] == "GET /orders/{order_id}")
        db = [s for s in spans if s["attributes"].get("db.system.name") == "postgresql"]
        assert db and all(s["parentSpanID"] == server["spanID"] for s in db), "Trace cần span DB (postgresql) là con của span HTTP"

        def job_traces():
            return [t for t in stack.jaeger_traces("olist-shop-worker") if any(s["name"] == "process olist:jobs" for s in t["spans"])]

        job = stack.eventually(job_traces, 60)
        assert job and {s["service"] for s in job[0]["spans"]} == {"olist-shop-api", "olist-shop-worker"}, \
            "Trace của job phải đi từ API qua Redis tới worker"

        for service in ("olist-shop-api", "olist-shop-worker"):
            envs = stack.eventually(lambda: resource_env(stack, service), 30)
            assert envs == {"lab"}, f"Span của {service} phải có resource attribute {ENV_KEY}=lab, đang là {envs}"

        calls = stack.prom_query('traces_span_metrics_calls_total{service_name="olist-shop-api", '
                                 'span_name="GET /orders/{order_id}", http_response_status_code="404"}', timeout=90)
        assert calls, "Prometheus chưa có spanmetrics của GET /orders/{order_id} kèm nhãn http_response_status_code"
        p95 = stack.prom_query('histogram_quantile(0.95, sum by (le) (traces_span_metrics_duration_milliseconds_bucket'
                               '{service_name="olist-shop-api", span_kind="SPAN_KIND_CLIENT"}))', timeout=30)
        assert p95 and p95[0]["value"][1] not in ("NaN", "+Inf"), "Histogram thời gian của span DB chưa dùng được với histogram_quantile"

        trace_id = traces[0]["traceID"]
        logs = stack.loki_query(f'{{service_name="olist-shop-api"}} | trace_id="{trace_id}"', timeout=60)
        lines = [json.loads(value) for stream in logs for _, value in stream["values"]]
        assert any(line.get("trace_id") == trace_id for line in lines), "Log của request không còn tới Loki kèm trace_id"
