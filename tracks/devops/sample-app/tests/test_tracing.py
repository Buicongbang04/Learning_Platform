import json
import logging
import os
import socket
import subprocess
import sys
from concurrent import futures
from pathlib import Path

import grpc
import pytest
from fastapi.testclient import TestClient
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2, logs_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2, trace_service_pb2_grpc

from olist_shop import seed, tracing, worker
from olist_shop.main import create_app
from olist_shop.settings import Settings

APP_DIR = Path(__file__).resolve().parents[1]
API_WITHOUT_ENDPOINT = """
import sys
import fakeredis
from fastapi.testclient import TestClient
from olist_shop import db, worker
from olist_shop.main import create_app
engine = db.make_engine("sqlite://")
queue = fakeredis.FakeRedis()
with TestClient(create_app(engine=engine, redis_client=queue)) as client:
    assert client.get("/healthz").status_code == 200
    assert client.post("/jobs/recompute").status_code == 202
assert "otel" not in queue.lindex(worker.QUEUE, 0).decode()
loaded = [n for n in sys.modules if n.startswith(("opentelemetry.exporter", "opentelemetry.sdk.trace", "grpc"))]
print(loaded or "ok")
"""
WORKER_WITHOUT_OTEL = """
import sys


class Blocked:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("opentelemetry", "grpc"):
            raise ModuleNotFoundError(name)


sys.meta_path.insert(0, Blocked())
import json
import fakeredis
from olist_shop import db, worker
engine = db.make_engine("sqlite://")
db.init(engine)
queue = fakeredis.FakeRedis()
queue.rpush(worker.QUEUE, json.dumps({"job_id": "j", "type": "recompute_revenue"}))
assert worker.run_once(queue, engine) == 1
print("ok")
"""


class Collector(trace_service_pb2_grpc.TraceServiceServicer, logs_service_pb2_grpc.LogsServiceServicer):
    def __init__(self):
        self.spans = []
        self.logs = []

    def Export(self, request, context):
        if isinstance(request, trace_service_pb2.ExportTraceServiceRequest):
            for resource_spans in request.resource_spans:
                service = _attrs(resource_spans.resource.attributes).get("service.name")
                for scope in resource_spans.scope_spans:
                    self.spans += [(service, span) for span in scope.spans]
            return trace_service_pb2.ExportTraceServiceResponse()
        for resource_logs in request.resource_logs:
            for scope in resource_logs.scope_logs:
                self.logs += list(scope.log_records)
        return logs_service_pb2.ExportLogsServiceResponse()


def _attrs(values) -> dict:
    out = {}
    for item in values:
        kind = item.value.WhichOneof("value")
        out[item.key] = getattr(item.value, kind) if kind else None
    return out


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def collector():
    sink = Collector()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    trace_service_pb2_grpc.add_TraceServiceServicer_to_server(sink, server)
    logs_service_pb2_grpc.add_LogsServiceServicer_to_server(sink, server)
    port = _free_port()
    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()
    sink.endpoint = f"http://127.0.0.1:{port}"
    yield sink
    server.stop(0)


@pytest.fixture
def endpoint(monkeypatch, collector):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", collector.endpoint)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    yield collector
    logging.getLogger().handlers.clear()


def _spans(collector, service=None):
    return [span for name, span in collector.spans if service in (None, name)]


def test_trace_exported_when_endpoint_set(endpoint, engine, fake_redis, olist_dir):
    seed.load(engine, olist_dir)
    app = create_app(settings=Settings(log_level="INFO"), engine=engine, redis_client=fake_redis)
    with TestClient(app) as client:
        assert client.get("/orders/o1").status_code == 200
        assert client.post("/jobs/recompute").status_code == 202
    spans = _spans(endpoint, "olist-shop-api")
    server = [s for s in spans if s.name == "GET /orders/{order_id}"]
    assert len(server) == 1 and server[0].kind == server[0].SPAN_KIND_SERVER
    attrs = _attrs(server[0].attributes)
    assert attrs["http.request.method"] == "GET" and attrs["http.route"] == "/orders/{order_id}"
    assert attrs["http.response.status_code"] == 200
    queries = [s for s in spans if s.trace_id == server[0].trace_id and s.kind == s.SPAN_KIND_CLIENT]
    assert len(queries) >= 2, "Mỗi query Postgres của request phải là một span con"
    for span in queries:
        assert span.parent_span_id == server[0].span_id
        query = _attrs(span.attributes)
        assert query["db.system.name"] == "sqlite" and query["db.query.text"].startswith("SELECT")
    publish = [s for s in spans if s.kind == s.SPAN_KIND_PRODUCER]
    assert [s.name for s in publish] == ["send olist:jobs"]

    tracer = tracing.setup("olist-shop-worker")
    tracer.instrument_engine(engine)
    assert worker.run_once(fake_redis, engine, tracer) == 1
    tracer.shutdown()
    jobs = [s for s in _spans(endpoint, "olist-shop-worker") if s.kind == s.SPAN_KIND_CONSUMER]
    assert len(jobs) == 1 and jobs[0].name == "process olist:jobs"
    assert jobs[0].trace_id == publish[0].trace_id and jobs[0].parent_span_id == publish[0].span_id, \
        "Context phải đi qua hàng đợi Redis: span của worker là con của span đẩy job"
    worker_db = [s for s in _spans(endpoint, "olist-shop-worker") if s.kind == s.SPAN_KIND_CLIENT]
    assert worker_db and all(s.parent_span_id == jobs[0].span_id for s in worker_db)


def test_traceparent_header_continues_trace(endpoint, engine, fake_redis):
    parent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
    with TestClient(create_app(engine=engine, redis_client=fake_redis)) as client:
        client.get("/healthz", headers={"traceparent": parent})
    server = [s for s in _spans(endpoint) if s.name == "GET /healthz"]
    assert server[0].trace_id.hex() == "0af7651916cd43dd8448eb211c80319c"
    assert server[0].parent_span_id.hex() == "b7ad6b7169203331"


def test_no_export_without_endpoint(monkeypatch, collector, engine, fake_redis, capsys):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", collector.endpoint)
    app = create_app(engine=engine, redis_client=fake_redis)
    with TestClient(app) as client:
        assert client.get("/healthz", headers={"X-Request-ID": "no-otel"}).status_code == 200
        assert client.post("/jobs/recompute").status_code == 202
    tracer = tracing.setup("olist-shop-worker")
    assert not tracer.enabled
    tracer.instrument_engine(engine)
    assert worker.run_once(fake_redis, engine, tracer) == 1
    tracer.shutdown()
    assert collector.spans == [] and collector.logs == []
    job = [line for line in capsys.readouterr().err.splitlines() if '"job done"' in line]
    assert job and json.loads(job[-1])["trace_id"] == "-"
    logging.getLogger().handlers.clear()
    env = {k: v for k, v in os.environ.items() if not k.startswith("OTEL_")}
    for script, why in ((API_WITHOUT_ENDPOINT, "API không nạp SDK, exporter hay gRPC khi thiếu endpoint"),
                        (WORKER_WITHOUT_OTEL, "worker chạy được khi không cài OpenTelemetry (bài Ansible chỉ có wheel "
                                              "trong setup/ansible-target/requirements-worker.txt)")):
        result = subprocess.run([sys.executable, "-c", script], cwd=APP_DIR, env=env, capture_output=True, text=True,
                                timeout=60)
        assert result.returncode == 0 and result.stdout.strip() == "ok", f"{why}:\n{result.stdout}{result.stderr[-2000:]}"


def test_log_has_trace_id(endpoint, engine, fake_redis, capsys):
    app = create_app(settings=Settings(log_level="INFO"), engine=engine, redis_client=fake_redis)
    with TestClient(app) as client:
        client.get("/healthz", headers={"X-Request-ID": "req-otel"})
        client.post("/jobs/recompute", headers={"X-Request-ID": "req-job"})
    tracer = tracing.setup("olist-shop-worker")
    assert worker.run_once(fake_redis, engine, tracer) == 1
    tracer.shutdown()
    events = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith("{")]
    request = next(e for e in events if e["request_id"] == "req-otel" and e["msg"] == "request")
    keys = list(request)
    assert keys.index("trace_id") == keys.index("request_id") + 1
    server = next(s for s in _spans(endpoint) if s.name == "GET /healthz")
    assert request["trace_id"] == server.trace_id.hex()
    enqueued = next(e for e in events if e["msg"] == "job enqueued")
    done = next(e for e in events if e["msg"] == "job done")
    assert done["trace_id"] == enqueued["trace_id"] != "-", "Log của worker phải cùng trace với request đẩy job"
    exported = [r for r in endpoint.logs if r.trace_id.hex() == request["trace_id"]]
    assert exported and json.loads(exported[0].body.string_value)["request_id"] == "req-otel", \
        "Log xuất qua OTLP (tới Loki) giữ nguyên dòng JSON"



BAD_PAYLOADS = {
    "deep-nesting": "[" * 200000,
    "list": json.dumps([1]),
    "traceparent-int": json.dumps({"job_id": "j", "otel": {"traceparent": 5}}),
    "baggage-int": json.dumps({"job_id": "j", "otel": {"baggage": 5}}),
    "carrier-list": json.dumps({"job_id": "j", "otel": [1]}),
}


@pytest.fixture(params=["tracing-on", "tracing-off"])
def worker_tracer(request, monkeypatch, collector):
    if request.param == "tracing-on":
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", collector.endpoint)
    else:
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    tracer = tracing.setup("olist-shop-worker")
    yield tracer
    tracer.shutdown()


@pytest.mark.parametrize("payload", BAD_PAYLOADS)
def test_bad_job_payload_counted_as_failed(worker_tracer, fake_redis, engine, payload):
    before = worker.REGISTRY.get_sample_value("jobs_failed_total") or 0.0
    fake_redis.rpush(worker.QUEUE, BAD_PAYLOADS[payload])
    assert worker.run_once(fake_redis, engine, worker_tracer) == 1
    assert worker.REGISTRY.get_sample_value("jobs_failed_total") == before + 1


@pytest.mark.parametrize("carrier", [{"traceparent": 5}, {"baggage": 5}, {"traceparent": "khong-hop-le"}])
def test_bad_carrier_does_not_block_valid_job(worker_tracer, fake_redis, engine, olist_dir, carrier):
    seed.load(engine, olist_dir)
    before = worker.REGISTRY.get_sample_value("jobs_processed_total") or 0.0
    fake_redis.rpush(worker.QUEUE, json.dumps({"job_id": "j", "type": "recompute_revenue", "otel": carrier}))
    assert worker.run_once(fake_redis, engine, worker_tracer) == 1
    assert worker.REGISTRY.get_sample_value("jobs_processed_total") == before + 1
