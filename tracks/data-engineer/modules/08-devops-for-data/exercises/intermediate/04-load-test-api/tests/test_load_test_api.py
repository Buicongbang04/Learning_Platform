"""Chấm bài load test. Test tự dựng server HTTP trên 127.0.0.1 (không cần mạng, không cần Docker).

Hai loại server:
- FakeServer: endpoint giả có độ trễ, lỗi và treo biết trước, để kiểm tra metric tính đúng.
- API metric của module 09 (lời giải bài intermediate 03 ở module 09) chạy trên DuckDB in-memory,
  để chạy một load test thật có SLO.
"""

import asyncio
import importlib.util
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

MODULES_DIR = Path(__file__).resolve().parents[5]
SERVING_PY = MODULES_DIR / "09-serving-bi/solutions/intermediate/03-metrics-api-cache/serving.py"


@pytest.fixture
def lt():
    return ex.module("loadtest.py")


@pytest.fixture(autouse=True)
def no_proxy(monkeypatch):
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


class FakeServer:
    """/ok trả 200 ngay; /slow?ms=N chờ N ms; /flaky cứ request thứ 4, 8, 12... trả 500; /hang chờ 1 giây."""

    def __init__(self):
        self.lock = threading.Lock()
        self.count = 0
        self.flaky_count = 0
        self.inflight = 0
        self.max_inflight = 0
        self.server = _Server(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def _handler(self):
        srv = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status):
                body = json.dumps({"status": status}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                parsed = urlparse(self.path)
                query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                with srv.lock:
                    srv.count += 1
                    srv.inflight += 1
                    srv.max_inflight = max(srv.max_inflight, srv.inflight)
                try:
                    if parsed.path == "/slow":
                        time.sleep(int(query.get("ms", "100")) / 1000)
                        return self._send(200)
                    if parsed.path == "/flaky":
                        with srv.lock:
                            srv.flaky_count += 1
                            n = srv.flaky_count
                        return self._send(500 if n % 4 == 0 else 200)
                    if parsed.path == "/hang":
                        time.sleep(1.0)
                        return self._send(200)
                    if parsed.path == "/ok":
                        return self._send(200)
                    return self._send(404)
                except (BrokenPipeError, ConnectionResetError):
                    pass            # client đã bỏ đi vì timeout
                finally:
                    with srv.lock:
                        srv.inflight -= 1

        return Handler


@pytest.fixture
def server():
    s = FakeServer()
    yield s
    s.close()


def _closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _fake_results(lt):
    """20 request, latency 10, 20, ..., 200 ms. Request thứ 7 trả 500, thứ 20 timeout."""
    out = []
    for i in range(1, 21):
        if i == 7:
            out.append(lt.Result(status=500, latency_s=i / 100))
        elif i == 20:
            out.append(lt.Result(status=None, latency_s=i / 100, error="ReadTimeout"))
        else:
            out.append(lt.Result(status=200, latency_s=i / 100))
    return out


# ---------------------------------------------------------------- tính metric (không cần server)


def test_percentile_nearest_rank(lt):
    assert lt.percentile([40, 10, 30, 20], 50) == 20
    assert lt.percentile([40, 10, 30, 20], 95) == 40
    assert lt.percentile([40, 10, 30, 20], 0) == 10
    assert lt.percentile([40, 10, 30, 20], 100) == 40
    values = list(range(100, 0, -1))
    assert lt.percentile(values, 95) == 95
    assert lt.percentile(values, 99) == 99
    with pytest.raises(ValueError):
        lt.percentile([], 50)
    with pytest.raises(ValueError):
        lt.percentile([1, 2], 101)


def test_result_ok(lt):
    assert lt.Result(status=200, latency_s=0.1).ok
    assert lt.Result(status=304, latency_s=0.1).ok
    assert not lt.Result(status=429, latency_s=0.1).ok
    assert not lt.Result(status=500, latency_s=0.1).ok
    assert not lt.Result(status=None, latency_s=0.1, error="ConnectError").ok


def test_summarize(lt):
    s = lt.summarize(_fake_results(lt), wall_time_s=2.0)
    assert s["requests"] == 20
    assert s["errors"] == 2
    assert s["error_rate"] == pytest.approx(0.1)
    assert s["throughput_rps"] == pytest.approx(10.0)
    assert s["p50_ms"] == pytest.approx(100.0)
    assert s["p95_ms"] == pytest.approx(190.0)
    assert s["p99_ms"] == pytest.approx(200.0)
    assert s["max_ms"] == pytest.approx(200.0)
    with pytest.raises(ValueError):
        lt.summarize([], wall_time_s=1.0)


def test_check_slo(lt):
    s = lt.summarize(_fake_results(lt), wall_time_s=2.0)
    assert lt.check_slo(s, lt.SLO(p95_ms=190, max_error_rate=0.1, min_throughput_rps=10)) == []
    assert lt.check_slo(s, lt.SLO(p95_ms=150, max_error_rate=0.01, min_throughput_rps=50)) == [
        "p95_ms", "error_rate", "throughput_rps",
    ]
    assert lt.check_slo(s, lt.SLO(p95_ms=500, max_error_rate=0.05)) == ["error_rate"]


# ---------------------------------------------------------------- bắn tải vào server giả


def test_run_load_counts_every_request(lt, server):
    results, wall = asyncio.run(lt.run_load(f"{server.url}/ok", total_requests=30, concurrency=5))
    assert len(results) == 30
    assert all(r.status == 200 and r.ok for r in results)
    assert server.count == 30
    assert wall > 0


def test_run_load_respects_concurrency_and_is_parallel(lt, server):
    results, wall = asyncio.run(
        lt.run_load(f"{server.url}/slow?ms=100", total_requests=20, concurrency=5)
    )
    assert len(results) == 20
    assert server.max_inflight <= 5, "không được mở quá `concurrency` request cùng lúc"
    assert server.max_inflight >= 3, "các request phải chạy song song"
    assert wall < 1.2, f"20 request 100 ms với 5 luồng phải mất khoảng 0,4 s, đo được {wall:.2f} s"
    assert all(r.latency_s >= 0.095 for r in results)


def test_run_load_records_http_errors(lt, server):
    results, _ = asyncio.run(lt.run_load(f"{server.url}/flaky", total_requests=40, concurrency=4))
    assert sum(r.status == 500 for r in results) == 10
    assert sum(r.ok for r in results) == 30


def test_run_load_timeout_is_an_error_not_a_crash(lt, server):
    results, wall = asyncio.run(
        lt.run_load(f"{server.url}/hang", total_requests=3, concurrency=3, timeout_s=0.2)
    )
    assert len(results) == 3
    assert all(r.status is None and r.error for r in results)
    assert all(0.15 <= r.latency_s < 0.9 for r in results)
    assert wall < 0.9


def test_run_load_connection_refused(lt):
    url = f"http://127.0.0.1:{_closed_port()}/ok"
    results, _ = asyncio.run(lt.run_load(url, total_requests=4, concurrency=2, timeout_s=0.5))
    assert len(results) == 4
    assert all(r.status is None and r.error for r in results)


def test_load_test_fails_slo_when_slow(lt, server):
    report = lt.load_test(
        f"{server.url}/slow?ms=150", total_requests=10, concurrency=5,
        slo=lt.SLO(p95_ms=100, max_error_rate=0.0),
    )
    assert report["passed"] is False
    assert report["violations"] == ["p95_ms"]
    assert report["requests"] == 10 and report["errors"] == 0
    assert report["p95_ms"] >= 150


# ---------------------------------------------------------------- load test API serving của module 09


def _load_serving():
    spec = importlib.util.spec_from_file_location("m09_serving_for_loadtest", SERVING_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def metrics_api():
    serving = _load_serving()
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE agg_daily_sales AS
        SELECT DATE '2018-01-01' + INTERVAL (i % 240) DAY AS order_date,
               ['SP', 'RJ', 'MG', 'RS', 'PR'][1 + i % 5] AS customer_state,
               1 + i % 7 AS orders,
               round(50 + (i * 37) % 900, 2) AS revenue
        FROM range(1200) t(i)
    """)
    service = serving.MetricsService(con, serving.TTLCache(ttl=30))
    db_lock = threading.Lock()             # một connection DuckDB dùng chung: tuần tự hoá truy cập

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            if parsed.path != "/daily_sales":
                status, body = 404, {"error": "not found"}
            else:
                with db_lock:
                    status, body = serving.handle_request(service, query)
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    srv = _Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", service
    srv.shutdown()
    srv.server_close()
    con.close()


def test_load_test_module09_api_meets_slo(lt, metrics_api):
    base, service = metrics_api
    url = f"{base}/daily_sales?state=SP&start=2018-01-01&end=2018-03-31&limit=50"
    report = lt.load_test(url, total_requests=60, concurrency=6,
                          slo=lt.SLO(p95_ms=1000, max_error_rate=0.0, min_throughput_rps=5))
    assert report["requests"] == 60 and report["errors"] == 0
    assert report["passed"] is True and report["violations"] == []
    assert service.cache.hits >= 50, "cùng tham số thì phần lớn request phải trúng cache"


def test_load_test_module09_bad_request_counts_as_error(lt, metrics_api):
    base, _ = metrics_api
    report = lt.load_test(f"{base}/daily_sales?start=2018-01-01&end=2018-01-31&limit=abc",
                          total_requests=10, concurrency=2, slo=lt.SLO(p95_ms=1000, max_error_rate=0.0))
    assert report["error_rate"] == pytest.approx(1.0)
    assert report["passed"] is False and "error_rate" in report["violations"]
