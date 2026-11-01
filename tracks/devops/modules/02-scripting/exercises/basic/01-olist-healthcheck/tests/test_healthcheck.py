import json
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Cần bash")


class FakeApi:
    def __init__(self):
        self.routes = {}
        self.calls = []
        self.release = threading.Event()
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                api.calls.append(self.path)
                status, body, delay = api.routes.get(self.path, (404, '{"detail":"Not Found"}', 0))
                if delay:
                    api.release.wait(delay)
                data = body.encode()
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def route(self, path, status, body, delay=0.0):
        self.routes[path] = (status, body if isinstance(body, str) else json.dumps(body), delay)

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def api():
    server = FakeApi()
    server.route("/healthz", 200, {"status": "ok", "version": "dev"})
    server.route("/readyz", 200, {"db": "ok", "redis": "ok"})
    yield server
    server.close()


@pytest.fixture(autouse=True)
def tools():
    ex.require_tool("curl", min_version="7.68")
    ex.require_tool("jq", min_version="1.6")


@pytest.fixture
def run(tmp_path):
    def runner(*args, env_extra=None):
        env = {"NO_PROXY": "*", **(env_extra or {})}
        start = time.monotonic()
        result = run_sandboxed(
            [BASH, ex.path("healthcheck.sh"), *map(str, args)], writable=[tmp_path], cwd=tmp_path, env=env, timeout=60
        )
        return result, time.monotonic() - start

    return runner


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_all_ok(api, run):
    result, _ = run("-u", api.url)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "OK - healthz=200 readyz=200 db=ok redis=ok\n"


def test_redis_down_is_warning(api, run):
    api.route("/readyz", 503, {"db": "ok", "redis": "error"})
    result, _ = run("-u", api.url)
    assert result.returncode == 1, result.stderr
    assert result.stdout == "WARNING - healthz=200 readyz=503 db=ok redis=error\n"


@pytest.mark.parametrize("redis", ["ok", "error"])
def test_db_down_is_critical(api, redis, run):
    api.route("/readyz", 503, {"db": "error", "redis": redis})
    result, _ = run("-u", api.url)
    assert result.returncode == 2, result.stderr
    assert result.stdout == f"CRITICAL - healthz=200 readyz=503 db=error redis={redis}\n"


def test_liveness_failure_skips_readiness(api, run):
    api.route("/healthz", 500, {"detail": "boom"})
    result, _ = run("-u", api.url)
    assert result.returncode == 2, result.stderr
    assert result.stdout == "CRITICAL - healthz=500\n"
    assert "/readyz" not in api.calls, "/healthz đã hỏng thì không gọi /readyz"


def test_connection_refused_is_critical(run):
    result, _ = run("-u", f"http://127.0.0.1:{free_port()}")
    assert result.returncode == 2, result.stderr
    assert result.stdout == "CRITICAL - api unreachable (curl exit 7)\n"


def test_timeout_is_critical_and_bounded(api, run):
    api.route("/healthz", 200, {"status": "ok"}, delay=20)
    result, elapsed = run("-u", api.url, "-t", "1")
    assert result.returncode == 2, result.stderr
    assert result.stdout == "CRITICAL - api unreachable (curl exit 28)\n"
    assert elapsed < 10, "Mỗi request phải có giới hạn thời gian bằng -t"
    assert "/readyz" not in api.calls


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, "not json"),
        (200, {"db": "error", "redis": "ok"}),
        (503, {"db": "ok", "redis": "ok"}),
        (503, {"db": "ok"}),
        (503, {"db": "broken", "redis": "ok"}),
        (404, {"detail": "Not Found"}),
    ],
)
def test_unexpected_readiness_is_unknown(api, status, body, run):
    api.route("/readyz", status, body)
    result, _ = run("-u", api.url)
    assert result.returncode == 3, result.stdout + result.stderr
    assert result.stdout == f"UNKNOWN - unexpected readyz response (status {status})\n"


def test_default_url_from_env(api, run):
    result, _ = run(env_extra={"OLIST_SHOP_API_URL": api.url})
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("OK - ")


def test_default_url_from_port(api, run):
    result, _ = run(env_extra={"OLIST_SHOP_API_PORT": str(api.port)})
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("OK - ")


def test_option_overrides_env(api, run):
    result, _ = run("-u", api.url, env_extra={"OLIST_SHOP_API_URL": f"http://127.0.0.1:{free_port()}"})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("args", [("-x",), ("-t", "0"), ("-t", "abc"), ("-t",), ("extra",)])
def test_usage_errors(args, run):
    result, _ = run(*args)
    assert result.returncode == 3
    assert result.stderr.startswith("Usage:")
    assert result.stdout == ""


def test_repeated_runs_are_stable(api, run):
    outputs = {run("-u", api.url)[0].stdout for _ in range(3)}
    assert outputs == {"OK - healthz=200 readyz=200 db=ok redis=ok\n"}


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(ex.path("healthcheck.sh"))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
