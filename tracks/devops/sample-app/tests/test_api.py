import json
import logging
import re
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from olist_shop import worker
from olist_shop.main import create_app
from olist_shop.settings import Settings

COMPOSE = Path(__file__).resolve().parent.parent / "compose.yaml"


def test_settings_defaults(monkeypatch):
    for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL", "APP_VERSION"):
        monkeypatch.delenv(key, raising=False)
    s = Settings()
    assert s.database_url == "sqlite:///./olist_shop.db"
    assert s.redis_url == "redis://localhost:26379/0"
    assert s.log_level == "INFO"
    assert s.app_version == "dev"


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")
    s = Settings()
    assert s.app_version == "1.2.3"
    assert s.database_url == "postgresql+psycopg://u:p@db/x"


def test_healthz_no_dependencies(client_without_db):
    r = client_without_db.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": Settings().app_version}


def test_healthz_reports_version(engine, fake_redis):
    app = create_app(settings=Settings(app_version="9.9.9"), engine=engine, redis_client=fake_redis)
    assert TestClient(app).get("/healthz").json() == {"status": "ok", "version": "9.9.9"}


def test_readyz_all_ok(client):
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json() == {"db": "ok", "redis": "ok"}


def test_readyz_reports_redis_down(engine, broken_redis):
    client = TestClient(create_app(engine=engine, redis_client=broken_redis))
    r = client.get("/readyz")
    assert r.status_code == 503 and r.json() == {"db": "ok", "redis": "error"}


def test_readyz_reports_db_down(broken_engine, fake_redis):
    client = TestClient(create_app(engine=broken_engine, redis_client=fake_redis))
    r = client.get("/readyz")
    assert r.status_code == 503 and r.json() == {"db": "error", "redis": "ok"}


def test_order_found_and_total(client_seeded):
    r = client_seeded.get("/orders/o1")
    assert r.status_code == 200
    body = r.json()
    assert body["order_id"] == "o1"
    assert body["customer_state"] == "SP"
    assert len(body["items"]) == 2
    assert body["total"] == 35.5


def test_order_missing_404(client_seeded):
    assert client_seeded.get("/orders/nope").status_code == 404


def test_recompute_then_stats(client_seeded, fake_redis, engine):
    r = client_seeded.post("/jobs/recompute")
    assert r.status_code == 202
    assert r.json()["job_id"]
    assert fake_redis.llen("olist:jobs") == 1
    assert worker.run_once(fake_redis, engine) == 1
    stats = client_seeded.get("/stats/revenue-by-state").json()
    assert stats[0] == {"state": "SP", "revenue": 35.5}
    assert stats[1] == {"state": "RJ", "revenue": 16.0}


def test_stats_empty_before_recompute(client_seeded):
    assert client_seeded.get("/stats/revenue-by-state").json() == []


def test_metrics_counts_requests(client):
    client.get("/healthz")
    text = client.get("/metrics").text
    assert 'http_requests_total{method="GET",path="/healthz",status="200"}' in text
    assert "http_request_duration_seconds_bucket" in text


def test_metrics_counts_enqueued_jobs(client):
    client.post("/jobs/recompute")
    client.post("/jobs/recompute")
    assert "jobs_enqueued_total 2.0" in client.get("/metrics").text


def test_metrics_path_is_route_template(client_seeded):
    for order_id in ("o1", "o2", "o3"):
        assert client_seeded.get(f"/orders/{order_id}").status_code == 200
    text = client_seeded.get("/metrics").text
    series = [line for line in text.splitlines()
              if line.startswith("http_requests_total{") and "/orders/" in line]
    assert series == ['http_requests_total{method="GET",path="/orders/{order_id}",status="200"} 3.0']


def test_metrics_unmatched_path_collapsed(client):
    client.get("/random/a")
    client.get("/random/b")
    text = client.get("/metrics").text
    assert "/random/" not in text
    assert 'path="unmatched",status="404"} 2.0' in text


def test_request_id_roundtrip(client):
    assert client.get("/healthz", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"


def test_request_id_generated(client):
    assert client.get("/healthz").headers["X-Request-ID"]


def test_log_is_one_json_line(engine, fake_redis, capsys):
    app = create_app(settings=Settings(log_level="INFO"), engine=engine, redis_client=fake_redis)
    with TestClient(app) as client:
        client.get("/healthz", headers={"X-Request-ID": "req-42"})
    lines = [line for line in capsys.readouterr().err.splitlines() if "req-42" in line]
    assert lines
    event = json.loads(lines[-1])
    assert {"ts", "level", "msg", "request_id"} <= event.keys()
    assert event["request_id"] == "req-42"
    assert event["level"] == "INFO"
    logging.getLogger().handlers.clear()


def test_ports_avoid_common_defaults():
    spec = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert spec["name"] == "olist-shop"
    defaults = []
    for name, service in spec["services"].items():
        assert service.get("cpuset") == "${DEVOPS_CPUSET:-}", name
        for port in service.get("ports", []):
            bind, _, rest = str(port).partition(":")
            assert bind == "127.0.0.1", f"{name}: chỉ publish trên 127.0.0.1, không mở ra mạng ngoài: {port}"
            host = rest.rsplit(":", 1)[0]
            m = re.fullmatch(r"\$\{OLIST_SHOP_\w+_PORT:-(\d+)\}", host)
            assert m, f"{name}: cổng host phải lấy từ biến OLIST_SHOP_*_PORT: {port}"
            defaults.append(int(m.group(1)))
    assert sorted(defaults) == [25432, 26379, 28000]
    assert not set(defaults) & {5432, 6379, 8000, 8080, 9000, 9001, 15432, 16379}



def test_500_has_request_id(broken_engine, fake_redis):
    client = TestClient(create_app(engine=broken_engine, redis_client=fake_redis), raise_server_exceptions=False)
    r = client.get("/orders/o1", headers={"X-Request-ID": "req-500"})
    assert r.status_code == 500
    assert r.headers.get("X-Request-ID") == "req-500"
    assert r.json() == {"error": "internal server error"}
    generated = client.get("/orders/o1")
    assert generated.status_code == 500 and len(generated.headers.get("X-Request-ID", "")) == 32


def test_500_is_counted_in_metrics(broken_engine, fake_redis):
    client = TestClient(create_app(engine=broken_engine, redis_client=fake_redis), raise_server_exceptions=False)
    client.get("/orders/o1")
    body = client.get("/metrics").text
    assert 'http_requests_total{method="GET",path="/orders/{order_id}",status="500"} 1.0' in body


def test_recompute_503_when_redis_down(engine, broken_redis):
    client = TestClient(create_app(engine=engine, redis_client=broken_redis))
    r = client.post("/jobs/recompute", headers={"X-Request-ID": "req-503"})
    assert r.status_code == 503
    assert r.json() == {"error": "redis unavailable"}
    assert r.headers.get("X-Request-ID") == "req-503"
    assert 'jobs_enqueued_total 0.0' in client.get("/metrics").text


def test_engine_connect_timeout(monkeypatch, tmp_path):
    from olist_shop import db

    calls = []
    monkeypatch.setattr(db, "create_engine", lambda url, **kwargs: calls.append((url, kwargs)))
    db.make_engine("postgresql+psycopg://olist:olist@postgres:5432/olist")
    db.make_engine("postgresql://olist:olist@postgres:5432/olist")
    db.make_engine(f"sqlite:///{tmp_path / 'shop.db'}")
    assert calls[0][1]["connect_args"] == {"connect_timeout": 3}
    assert calls[1][1]["connect_args"] == {"connect_timeout": 3}
    assert "connect_args" not in calls[2][1], "sqlite3 không nhận connect_timeout"
    assert all(kwargs["pool_pre_ping"] for _, kwargs in calls)
