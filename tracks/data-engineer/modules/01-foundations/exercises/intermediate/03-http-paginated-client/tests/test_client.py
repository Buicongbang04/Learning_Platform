"""Test chạy một HTTP server giả lập trên 127.0.0.1 (không cần Internet)."""

import inspect
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from testkit import Exercise

ex = Exercise(__file__)

TOKEN = "secret"
ORDERS = [{"order_id": f"o{i}", "order_status": "delivered"} for i in range(1, 8)]


class FakeApi:
    def __init__(self):
        self.requests = []          # (path, query dict, headers dict)
        self.failures = []          # các (status, headers) trả trước khi trả kết quả thật
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def count(self, path):
        return sum(1 for p, _, _ in self.requests if p == path)

    def _handler(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body=None, headers=None):
                payload = json.dumps(body if body is not None else {"error": status}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                parsed = urlparse(self.path)
                query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                api.requests.append((parsed.path, query, dict(self.headers)))
                if parsed.path == "/missing":
                    return self._send(404)
                if parsed.path == "/orders" and self.headers.get("Authorization") != f"Bearer {TOKEN}":
                    return self._send(401)
                if api.failures:
                    status, headers = api.failures.pop(0)
                    return self._send(status, headers=headers)
                if parsed.path == "/flaky":
                    return self._send(200, {"ok": True})
                if parsed.path == "/orders":
                    start = int(query.get("cursor", 0))
                    limit = int(query.get("limit", 100))
                    end = start + limit
                    nxt = str(end) if end < len(ORDERS) else None
                    return self._send(200, {"data": ORDERS[start:end], "next_cursor": nxt})
                return self._send(404)

        return Handler


@pytest.fixture(autouse=True)
def no_proxy(monkeypatch):
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


@pytest.fixture()
def api():
    server = FakeApi()
    yield server
    server.close()


@pytest.fixture(scope="module")
def client():
    return ex.module("client.py")


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


def test_backoff_delay(client):
    assert [client.backoff_delay(a) for a in range(4)] == [0.5, 1.0, 2.0, 4.0]
    assert client.backoff_delay(10, base=1, cap=30) == 30
    assert client.backoff_delay(2, base=0.1) == pytest.approx(0.4)


def test_get_json_success_without_sleep(client, api):
    sleeps = Sleeps()
    with requests.Session() as s:
        assert client.get_json(s, api.url + "/flaky", sleep=sleeps) == {"ok": True}
    assert sleeps == []


def test_retries_5xx_with_exponential_backoff(client, api):
    api.failures = [(503, {}), (502, {})]
    sleeps = Sleeps()
    with requests.Session() as s:
        assert client.get_json(s, api.url + "/flaky", sleep=sleeps) == {"ok": True}
    assert sleeps == [0.5, 1.0]
    assert api.count("/flaky") == 3


def test_respects_retry_after_on_429(client, api):
    api.failures = [(429, {"Retry-After": "2"})]
    sleeps = Sleeps()
    with requests.Session() as s:
        client.get_json(s, api.url + "/flaky", sleep=sleeps)
    assert sleeps == [2.0]


def test_gives_up_after_max_retries(client, api):
    api.failures = [(503, {})] * 10
    sleeps = Sleeps()
    with requests.Session() as s, pytest.raises(requests.HTTPError):
        client.get_json(s, api.url + "/flaky", max_retries=3, sleep=sleeps)
    assert api.count("/flaky") == 4
    assert sleeps == [0.5, 1.0, 2.0]


def test_does_not_retry_404(client, api):
    sleeps = Sleeps()
    with requests.Session() as s, pytest.raises(requests.HTTPError):
        client.get_json(s, api.url + "/missing", sleep=sleeps)
    assert api.count("/missing") == 1
    assert sleeps == []


def test_retries_connection_error(client):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()  # cổng không ai nghe => Connection refused
    sleeps = Sleeps()
    with requests.Session() as s, pytest.raises(requests.ConnectionError):
        client.get_json(s, f"http://127.0.0.1:{port}/x", max_retries=2, sleep=sleeps)
    assert sleeps == [0.5, 1.0]


def test_always_sets_timeout(client, api):
    seen = {}

    class RecordingSession(requests.Session):
        def get(self, url, **kwargs):
            seen.update(kwargs)
            return super().get(url, **kwargs)

    with RecordingSession() as s:
        client.get_json(s, api.url + "/flaky", sleep=Sleeps())
    assert seen.get("timeout"), "Phải truyền timeout cho session.get"


def test_iter_orders_paginates_lazily(client, api):
    pages = client.iter_orders(api.url, TOKEN, page_size=3, sleep=Sleeps())
    assert inspect.isgenerator(pages)
    assert api.count("/orders") == 0, "Generator không được gọi API trước khi được duyệt"
    assert [o["order_id"] for o in pages] == [f"o{i}" for i in range(1, 8)]
    order_requests = [(q, h) for p, q, h in api.requests if p == "/orders"]
    assert len(order_requests) == 3
    assert "cursor" not in order_requests[0][0]
    assert order_requests[1][0] == {"limit": "3", "cursor": "3"}
    assert order_requests[0][1].get("Authorization") == f"Bearer {TOKEN}"


def test_iter_orders_survives_transient_errors(client, api):
    api.failures = [(500, {}), (429, {"Retry-After": "1"})]
    sleeps = Sleeps()
    got = list(client.iter_orders(api.url, TOKEN, page_size=5, sleep=sleeps))
    assert len(got) == 7
    assert sleeps == [0.5, 1.0]


def test_iter_orders_bad_token_fails_fast(client, api):
    sleeps = Sleeps()
    with pytest.raises(requests.HTTPError):
        list(client.iter_orders(api.url, "wrong", sleep=sleeps))
    assert api.count("/orders") == 1
    assert sleeps == []
