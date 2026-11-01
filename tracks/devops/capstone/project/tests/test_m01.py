"""M01: bootstrap.sh, healthcheck.sh, backup.sh. Hợp đồng đầy đủ ở capstone/milestones/m01-ops-scripts.md."""

import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from testkit import ROOT, DockerLab, Exercise, free_port, run_sandboxed, sandbox_command

BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Cần bash")
FIXTURES = Path(__file__).parent / "fixtures"
CAPSTONE = Path(__file__).resolve().parents[2]
OPS = ("bootstrap.sh", "healthcheck.sh", "backup.sh")
TS = "20261101T020000Z"
OLD = [f"202610{d:02d}T020000Z" for d in range(20, 28)]
PROJECT = "olist-shop-m01test"
READY = {"db": "ok", "redis": "ok"}
REDIS_DOWN = {"db": "ok", "redis": "error"}
ENV_EXAMPLE = (CAPSTONE.parent / "sample-app" / ".env.example").read_text(encoding="utf-8")
COMPOSE_STUB = "name: olist-shop\nservices:\n  api:\n    image: olist-shop:dev\n"
DESTRUCTIVE = {"down", "rm", "kill", "stop", "prune", "volume", "system"}

FAKE_PG_DUMP = r"""#!/usr/bin/env bash
out=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[$i]}" in
    -f) out="${args[$((i + 1))]}" ;;
    -f*) out="${args[$i]#-f}" ;;
    --file=*) out="${args[$i]#--file=}" ;;
    --file) out="${args[$((i + 1))]}" ;;
  esac
done
"$FAKE_PYTHON" - "$FAKE_PG_LOG" "$@" <<'PY'
import json, os, sys
keys = ("PGHOST", "PGPORT", "PGUSER", "PGDATABASE", "PGPASSWORD")
with open(sys.argv[1], "a") as fh:
    fh.write(json.dumps({"argv": sys.argv[2:], "env": {k: os.environ.get(k) for k in keys}}) + "\n")
PY
write() {
  if [[ -n "$out" ]]; then printf '%s' "$1" > "$out"; else printf '%s' "$1"; fi
}
case "${FAKE_PG_MODE:-ok}" in
  ok) write "PGDMP fake dump of ${PGDATABASE:-?} $(date +%s%N)" ;;
  empty) write "" ;;
  fail)
    write "PGDMP partial"
    echo 'pg_dump: error: connection to server failed' >&2
    exit 1
    ;;
  slow)
    write "PGDMP partial"
    : > "$FAKE_STARTED"
    for _ in $(seq 1 600); do sleep 0.1; done
    ;;
  selfterm)
    write "PGDMP partial"
    kill -TERM 0
    for _ in $(seq 1 100); do sleep 0.1; done
    ;;
esac
"""

FAKE_DOCKER = r"""#!/usr/bin/env bash
"$FAKE_PYTHON" - "$FAKE_DOCKER_LOG" "$@" <<'PY'
import json, os, sys
with open(sys.argv[1], "a") as fh:
    fh.write(json.dumps({"argv": sys.argv[2:], "cwd": os.getcwd(), "cpuset": os.environ.get("DEVOPS_CPUSET")}) + "\n")
PY
mode="${FAKE_DOCKER_MODE:-ok}"
if [[ "${1:-}" == compose && "$mode" == nocompose ]]; then
  echo "docker: 'compose' is not a docker command." >&2
  exit 1
fi
if [[ "${1:-}" == compose && "${2:-}" == version ]]; then
  echo "Docker Compose version v2.29.7"
  exit 0
fi
if [[ "${1:-}" == compose && " $* " == *" up "* && "$mode" == upfail ]]; then
  echo "Error response from daemon: fake up failure" >&2
  exit 1
fi
exit 0
"""


def require_file(path: Path) -> Path:
    if not path.is_file():
        shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        pytest.fail(f"Chưa có tệp {shown}. Xem tracks/devops/capstone/milestones/m01-ops-scripts.md")
    return path


class FakeApi:
    """API giả trên loopback. `readyz` là chuỗi response trả lần lượt; phần tử cuối lặp lại mãi."""

    def __init__(self):
        self.readyz = [(200, READY, 0.0)]
        self.calls: list[str] = []
        self.lock = threading.Lock()
        self.release = threading.Event()
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with api.lock:
                    api.calls.append(self.path)
                    if self.path == "/readyz":
                        status, body, delay = api.readyz[0] if len(api.readyz) == 1 else api.readyz.pop(0)
                    elif self.path == "/healthz":
                        status, body, delay = 200, {"status": "ok", "version": "dev"}, 0.0
                    else:
                        status, body, delay = 404, {"detail": "Not Found"}, 0.0
                if delay:
                    api.release.wait(delay)
                data = (body if isinstance(body, str) else json.dumps(body)).encode()
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
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def respond(self, *responses):
        with self.lock:
            self.readyz = [(status, body, delay) for status, body, delay in (r if len(r) == 3 else (*r, 0.0) for r in responses)]

    def readyz_calls(self) -> int:
        with self.lock:
            return self.calls.count("/readyz")

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()


class Ops:
    """Chạy script trong ops/ của `root` bằng sandbox, với pg_dump và docker giả đứng đầu PATH."""

    def __init__(self, tmp: Path, root: Path):
        self.tmp = tmp
        self.root = root
        self.bin = tmp / "bin"
        self.bin.mkdir(exist_ok=True)
        for name, text in {"pg_dump": FAKE_PG_DUMP, "docker": FAKE_DOCKER}.items():
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        self.pg_log = tmp / "pg_dump.jsonl"
        self.docker_log = tmp / "docker.jsonl"
        self.started = tmp / "pg_dump.started"

    def script(self, name: str) -> Path:
        return require_file(self.root / "ops" / name)

    def env(self, extra: dict | None = None) -> dict:
        env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '/usr/bin:/bin')}",
            "FAKE_PYTHON": sys.executable,
            "FAKE_PG_LOG": str(self.pg_log),
            "FAKE_DOCKER_LOG": str(self.docker_log),
            "FAKE_STARTED": str(self.started),
            "NO_PROXY": "*",
        }
        env.update({k: str(v) for k, v in (extra or {}).items()})
        return env

    def run(self, name: str, *args, env: dict | None = None, script: Path | None = None, timeout: float = 90):
        path = script or self.script(name)
        start = time.monotonic()
        result = run_sandboxed([BASH, path, *map(str, args)], writable=[self.tmp], cwd=self.tmp, env=self.env(env),
                               timeout=timeout)
        result.elapsed = time.monotonic() - start
        return result

    def popen(self, name: str, *args, env: dict | None = None) -> subprocess.Popen:
        argv = sandbox_command([BASH, self.script(name), *map(str, args)], writable=[self.tmp], cwd=self.tmp,
                               env=self.env(env))
        return subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env={},
                                start_new_session=True)

    @staticmethod
    def _jsonl(path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def pg_calls(self) -> list[dict]:
        return self._jsonl(self.pg_log)

    def docker_calls(self) -> list[dict]:
        return self._jsonl(self.docker_log)

    def stage(self, api_port: int | None = None) -> tuple[Path, Path]:
        """Chép ops/ vào một repo giả `repo/capstone/project/ops`, cạnh `repo/sample-app` (compose.yaml giả)."""
        bootstrap = self.script("bootstrap.sh")
        ops_dir = self.tmp / "repo" / "capstone" / "project" / "ops"
        app = self.tmp / "repo" / "sample-app"
        ops_dir.mkdir(parents=True, exist_ok=True)
        app.mkdir(parents=True, exist_ok=True)
        for name in OPS:
            source = bootstrap.parent / name
            if source.is_file():
                shutil.copy2(source, ops_dir / name)
        (app / "compose.yaml").write_text(COMPOSE_STUB)
        example = ENV_EXAMPLE
        if api_port is not None:
            example = example.replace("OLIST_SHOP_API_PORT=28000", f"OLIST_SHOP_API_PORT={api_port}")
        (app / ".env.example").write_text(example)
        return ops_dir / "bootstrap.sh", app


@pytest.fixture
def ops(tmp_path, project_root):
    return Ops(tmp_path, project_root)


@pytest.fixture
def api():
    server = FakeApi()
    yield server
    server.close()


@pytest.fixture
def healthcheck_tools():
    Exercise.require_tool("curl", min_version="7.68")
    Exercise.require_tool("jq", min_version="1.6")


@pytest.fixture
def backup_tools():
    Exercise.require_tool("flock")
    Exercise.require_tool("sha256sum")


GLOBAL_WITH_VALUE = {"-p", "--project-name", "-f", "--file", "--project-directory", "--env-file", "--profile", "--ansi",
                     "--progress", "--parallel"}


def compose_up(call: dict) -> dict | None:
    """Tách một lệnh `docker compose ... up ...` thành project, file và cờ của `up`; None nếu không phải lệnh up."""
    argv = call["argv"]
    if not argv or argv[0] != "compose":
        return None
    project, files, i = None, [], 1
    while i < len(argv) and argv[i].startswith("-"):
        flag, _, inline = argv[i].partition("=")
        value = inline if inline else (argv[i + 1] if flag in GLOBAL_WITH_VALUE and i + 1 < len(argv) else None)
        if flag in ("-p", "--project-name"):
            project = value
        elif flag in ("-f", "--file"):
            files.append(value)
        i += 1 if inline or flag not in GLOBAL_WITH_VALUE else 2
    if i >= len(argv) or argv[i] != "up":
        return None
    cwd = Path(call.get("cwd") or "/")
    return {"project": project, "files": [str((cwd / f).resolve()) for f in files if f], "args": argv[i + 1:],
            "cpuset": call.get("cpuset")}


def up_calls(ops: Ops) -> list[dict]:
    return [up for call in ops.docker_calls() if (up := compose_up(call))]


def destructive_calls(ops: Ops) -> list[list[str]]:
    return [call["argv"] for call in ops.docker_calls() if DESTRUCTIVE & set(call["argv"])]


def entries(path: Path) -> set[str]:
    return {p.name for p in path.iterdir()} if path.exists() else set()


def visible(path: Path) -> set[str]:
    return {name for name in entries(path) if not name.startswith(".")}


def hidden_dirs(path: Path) -> list[str]:
    return [p.name for p in path.iterdir() if p.name.startswith(".") and p.is_dir()] if path.exists() else []


def seed_backups(dest: Path, stamps) -> None:
    for stamp in stamps:
        folder = dest / stamp
        folder.mkdir(parents=True)
        (folder / "olist.dump").write_text(f"PGDMP old {stamp}")
        digest = hashlib.sha256((folder / "olist.dump").read_bytes()).hexdigest()
        (folder / "SHA256SUMS").write_text(f"{digest}  olist.dump\n")


def healthcheck_problems(ops: Ops, api: FakeApi) -> list[str]:
    found = []
    api.respond((503, REDIS_DOWN))
    result = ops.run("healthcheck.sh", "-u", api.url)
    if (result.returncode, result.stdout) != (1, "FAIL readyz=503 failing=redis\n"):
        found.append(f"/readyz 503 redis=error: cần exit 1 và 'FAIL readyz=503 failing=redis', "
                     f"nhận exit {result.returncode} stdout={result.stdout!r}")
    result = ops.run("healthcheck.sh", "-u", f"http://127.0.0.1:{free_port()}")
    if result.returncode != 1 or not result.stdout.startswith("FAIL api unreachable"):
        found.append(f"API không chạy: cần exit 1 và 'FAIL api unreachable...', nhận exit {result.returncode} "
                     f"stdout={result.stdout!r}")
    return found


def bootstrap_problems(ops: Ops, api: FakeApi) -> list[str]:
    script, app = ops.stage(api.port)
    env = {"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT}
    found = []
    api.respond((503, REDIS_DOWN), (200, READY))
    first = ops.run("bootstrap.sh", "-t", 30, env=env, script=script)
    lines = first.stdout.splitlines()
    if first.returncode != 0 or not lines or lines[-1] != f"ready http://127.0.0.1:{api.port}":
        found.append(f"Lần chạy đầu: cần exit 0 và dòng cuối stdout 'ready http://127.0.0.1:{api.port}' (cổng đọc từ .env), "
                     f"nhận exit {first.returncode} stdout={first.stdout!r} stderr={first.stderr[-800:]!r}")
    if api.readyz_calls() < 2:
        found.append(f"/readyz trả 503 ở lần hỏi đầu: bootstrap phải chờ và hỏi lại tới khi 200, mới hỏi {api.readyz_calls()} lần")
    env_file = app / ".env"
    if not env_file.is_file() or env_file.read_text() != (app / ".env.example").read_text():
        found.append(".env phải được tạo bằng cách chép nguyên .env.example khi chưa có")
    edited = (env_file.read_text() if env_file.is_file() else "") + "LOG_LEVEL=DEBUG\n"
    env_file.write_text(edited)
    second = ops.run("bootstrap.sh", "-t", 30, env=env, script=script)
    if second.returncode != 0:
        found.append(f"Lần chạy thứ hai phải exit 0, nhận {second.returncode}: {second.stderr[-800:]!r}")
    if env_file.read_text() != edited:
        found.append(".env đã có thì không được ghi đè (bạn vừa sửa LOG_LEVEL, bootstrap xoá mất)")
    ups = up_calls(ops)
    if len(ups) != 2:
        found.append(f"Mỗi lần chạy gọi đúng một lệnh 'docker compose ... up', thấy {len(ups)} lệnh up")
    for up in ups:
        if up["project"] != PROJECT or up["files"] != [str((app / "compose.yaml").resolve())]:
            found.append(f"Lệnh up phải có --project-name {PROJECT} và --file trỏ tới {app / 'compose.yaml'}, "
                         f"nhận project={up['project']!r} files={up['files']!r}")
        if not {"-d", "--detach"} & set(up["args"]):
            found.append(f"Lệnh up phải chạy nền (-d/--detach), nhận {up['args']}")
    if destructive_calls(ops):
        found.append(f"bootstrap không được chạy lệnh phá huỷ: {destructive_calls(ops)}")
    return found


def backup_problems(ops: Ops) -> list[str]:
    found = []
    dest = ops.tmp / "pb-fail"
    seed_backups(dest, OLD[:3])
    (dest / "notes.txt").write_text("giữ")
    before = visible(dest)
    result = ops.run("backup.sh", "-k", 1, "-d", dest, env={"BACKUP_TIMESTAMP": TS, "FAKE_PG_MODE": "fail"})
    if result.returncode != 1 or result.stdout or visible(dest) != before or hidden_dirs(dest):
        found.append(f"pg_dump lỗi: cần exit 1, stdout rỗng, không tạo/xoá gì; nhận exit {result.returncode} "
                     f"stdout={result.stdout!r}, thư mục còn {sorted(entries(dest))}")
    dest = ops.tmp / "pb-keep"
    seed_backups(dest, OLD[:4])
    (dest / "notes.txt").write_text("giữ")
    result = ops.run("backup.sh", "-k", 2, "-d", dest, env={"BACKUP_TIMESTAMP": TS})
    if result.returncode != 0 or visible(dest) != {TS, OLD[3], "notes.txt"}:
        found.append(f"-k 2: phải giữ {TS}, {OLD[3]} và không đụng notes.txt; nhận exit {result.returncode}, "
                     f"còn {sorted(visible(dest))}")
    calls = len(ops.pg_calls())
    again = ops.run("backup.sh", "-k", 2, "-d", dest, env={"BACKUP_TIMESTAMP": TS})
    if again.stdout != f"skip {dest}/{TS}\n" or len(ops.pg_calls()) != calls:
        found.append(f"Chạy lại cùng BACKUP_TIMESTAMP khi bản đó còn nguyên: phải in 'skip {dest}/{TS}' và không gọi "
                     f"pg_dump; nhận stdout={again.stdout!r}")
    return found


@pytest.mark.usefixtures("healthcheck_tools")
class TestM01Healthcheck:
    def test_m01_healthcheck_ok(self, ops, api):
        result = ops.run("healthcheck.sh", "-u", api.url)
        assert result.returncode == 0, result.stderr
        assert result.stdout == "OK db=ok redis=ok\n"

    def test_m01_healthcheck_core_contract(self, ops, api):
        found = healthcheck_problems(ops, api)
        assert not found, "\n".join(found)

    @pytest.mark.parametrize(("body", "failing"), [
        ({"db": "ok", "redis": "error"}, "redis"),
        ({"db": "error", "redis": "ok"}, "db"),
        ({"db": "error", "redis": "error"}, "db,redis"),
    ])
    def test_m01_healthcheck_names_failing_component(self, ops, api, body, failing):
        api.respond((503, body))
        result = ops.run("healthcheck.sh", "-u", api.url)
        assert result.returncode == 1, result.stderr
        assert result.stdout == f"FAIL readyz=503 failing={failing}\n"

    def test_m01_healthcheck_timeout_is_bounded(self, ops, api):
        api.respond((200, READY, 20))
        result = ops.run("healthcheck.sh", "-u", api.url, "-t", 1)
        assert result.returncode == 1, result.stderr
        assert result.stdout.startswith("FAIL api unreachable") and result.stdout.count("\n") == 1, result.stdout
        assert result.elapsed < 10, "Mỗi lần gọi /readyz phải có giới hạn thời gian -t"

    @pytest.mark.parametrize(("status", "body"), [
        (200, "not json"),
        (200, {"db": "error", "redis": "ok"}),
        (503, {"db": "ok", "redis": "ok"}),
        (503, {"db": "ok"}),
        (503, {"db": "broken", "redis": "ok"}),
        (404, {"detail": "Not Found"}),
        (500, "Internal Server Error"),
    ])
    def test_m01_healthcheck_unexpected_response(self, ops, api, status, body):
        api.respond((status, body))
        result = ops.run("healthcheck.sh", "-u", api.url)
        assert result.returncode == 1, result.stderr
        assert result.stdout == f"FAIL readyz={status} unexpected response\n"

    def test_m01_healthcheck_url_sources(self, ops, api):
        dead = f"http://127.0.0.1:{free_port()}"
        cases = [
            ((), {"OLIST_SHOP_API_URL": api.url}),
            ((), {"OLIST_SHOP_API_PORT": api.port}),
            ((), {"OLIST_SHOP_API_URL": api.url, "OLIST_SHOP_API_PORT": free_port()}),
            (("-u", api.url), {"OLIST_SHOP_API_URL": dead}),
            (("-u", api.url + "/"), {}),
        ]
        for args, env in cases:
            result = ops.run("healthcheck.sh", *args, env=env)
            assert result.returncode == 0, f"{args} {env}: {result.stdout}{result.stderr}"
        assert set(api.calls) <= {"/readyz", "/healthz"}, f"Đường dẫn gọi sai (vd. //readyz): {set(api.calls)}"

    def test_m01_healthcheck_single_try_without_wait(self, ops, api):
        api.respond((503, REDIS_DOWN))
        result = ops.run("healthcheck.sh", "-u", api.url)
        assert result.returncode == 1
        assert api.readyz_calls() == 1, "Không có -w thì chỉ hỏi /readyz một lần"

    def test_m01_healthcheck_waits_until_ready(self, ops, api):
        api.respond((503, REDIS_DOWN), (503, {"db": "error", "redis": "ok"}), (200, READY))
        result = ops.run("healthcheck.sh", "-u", api.url, "-w", 30)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout == "OK db=ok redis=ok\n", "Có -w thì stdout chỉ có dòng kết quả cuối cùng"
        assert api.readyz_calls() == 3

    def test_m01_healthcheck_wait_gives_up(self, ops, api):
        api.respond((503, REDIS_DOWN))
        result = ops.run("healthcheck.sh", "-u", api.url, "-w", 3, "-t", 2)
        assert result.returncode == 1, result.stderr
        assert result.stdout == "FAIL readyz=503 failing=redis\n"
        assert api.readyz_calls() >= 2, "Có -w thì phải hỏi lại trong lúc chờ"
        assert result.elapsed < 15, f"-w 3 -t 2 phải dừng sau khoảng 3–5 giây, chạy {result.elapsed:.1f} giây"

    @pytest.mark.parametrize("args", [("-x",), ("-t", "0"), ("-t", "abc"), ("-t",), ("-w", "-1"), ("-w", "x"), ("-u",),
                                      ("extra",)])
    def test_m01_healthcheck_usage_errors(self, ops, args):
        result = ops.run("healthcheck.sh", *args)
        assert result.returncode == 2, result.stdout + result.stderr
        assert result.stderr.startswith("Usage:")
        assert result.stdout == ""


@pytest.mark.usefixtures("healthcheck_tools")
class TestM01Bootstrap:
    def test_m01_bootstrap_core_contract(self, ops, api):
        found = bootstrap_problems(ops, api)
        assert not found, "\n".join(found)

    def test_m01_bootstrap_port_env_overrides_env_file(self, ops, api):
        script, app = ops.stage(free_port())
        env = {"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT, "OLIST_SHOP_API_PORT": api.port}
        result = ops.run("bootstrap.sh", "-t", 20, env=env, script=script)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout.splitlines()[-1] == f"ready http://127.0.0.1:{api.port}"

    def test_m01_bootstrap_finds_sample_app(self, ops, api):
        script, app = ops.stage(api.port)
        result = ops.run("bootstrap.sh", "-t", 20, env={"OLIST_SHOP_PROJECT": PROJECT}, script=script)
        assert result.returncode == 0, result.stdout + result.stderr
        [up] = up_calls(ops)
        assert up["files"] == [str((app / "compose.yaml").resolve())]

    def test_m01_bootstrap_default_project_name(self, ops, api):
        script, app = ops.stage(api.port)
        result = ops.run("bootstrap.sh", "-t", 20, env={"OLIST_SHOP_APP_DIR": app}, script=script)
        assert result.returncode == 0, result.stdout + result.stderr
        assert [up["project"] for up in up_calls(ops)] == ["olist-shop"]

    def test_m01_bootstrap_requires_compose(self, ops, api):
        script, app = ops.stage(api.port)
        env = {"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT, "FAKE_DOCKER_MODE": "nocompose"}
        result = ops.run("bootstrap.sh", "-t", 20, env=env, script=script)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "compose" in result.stderr.lower()
        assert not up_calls(ops)
        assert not (app / ".env").exists(), "Kiểm điều kiện trước khi thay đổi bất cứ thứ gì"

    def test_m01_bootstrap_requires_compose_file(self, ops, api):
        script, app = ops.stage(api.port)
        (app / "compose.yaml").unlink()
        result = ops.run("bootstrap.sh", "-t", 20, env={"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT},
                         script=script)
        assert result.returncode == 2, result.stdout + result.stderr
        assert not up_calls(ops)
        assert not (app / ".env").exists()

    def test_m01_bootstrap_up_failure(self, ops, api):
        script, app = ops.stage(api.port)
        env = {"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT, "FAKE_DOCKER_MODE": "upfail"}
        result = ops.run("bootstrap.sh", "-t", 20, env=env, script=script)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "fake up failure" in result.stderr, "Giữ nguyên thông báo lỗi của docker compose cho người vận hành"
        assert api.readyz_calls() == 0, "compose up lỗi thì dừng ngay, không chờ readiness"
        assert "ready " not in result.stdout

    def test_m01_bootstrap_not_ready_times_out(self, ops, api):
        script, app = ops.stage(api.port)
        api.respond((503, REDIS_DOWN))
        result = ops.run("bootstrap.sh", "-t", 3, env={"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT},
                         script=script)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "redis" in result.stdout + result.stderr, "Báo thành phần đang lỗi để người vận hành biết xem đâu"
        assert not [line for line in result.stdout.splitlines() if line.startswith("ready ")]
        assert result.elapsed < 20

    @pytest.mark.parametrize("cpuset", [None, "", "0-1"])
    def test_m01_bootstrap_passes_cpuset_through(self, ops, api, cpuset):
        script, app = ops.stage(api.port)
        env = {"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT}
        if cpuset is not None:
            env["DEVOPS_CPUSET"] = cpuset
        result = ops.run("bootstrap.sh", "-t", 20, env=env, script=script)
        assert result.returncode == 0, result.stdout + result.stderr
        [up] = up_calls(ops)
        expected = {None, ""} if not cpuset else {cpuset}
        assert up["cpuset"] in expected, f"bootstrap không được tự đặt DEVOPS_CPUSET, compose nhận {up['cpuset']!r}"

    @pytest.mark.parametrize("args", [("-t", "0"), ("-t", "x"), ("-t",), ("-z",), ("extra",)])
    def test_m01_bootstrap_usage_errors(self, ops, api, args):
        script, app = ops.stage(api.port)
        result = ops.run("bootstrap.sh", *args, env={"OLIST_SHOP_APP_DIR": app, "OLIST_SHOP_PROJECT": PROJECT},
                         script=script)
        assert result.returncode == 2, result.stdout + result.stderr
        assert result.stderr.startswith("Usage:")
        assert not up_calls(ops)


@pytest.mark.usefixtures("backup_tools")
class TestM01Backup:
    @pytest.fixture
    def dest(self, tmp_path):
        return tmp_path / "my backups" / "olist"

    def run(self, ops, *args, **env):
        env.setdefault("BACKUP_TIMESTAMP", TS)
        return ops.run("backup.sh", *args, env=env)

    def test_m01_backup_core_contract(self, ops):
        found = backup_problems(ops)
        assert not found, "\n".join(found)

    def test_m01_backup_creates_timestamped_dir(self, ops, dest):
        result = self.run(ops, "-d", dest)
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"created {dest}/{TS}\n"
        folder = dest / TS
        assert entries(folder) == {"olist.dump", "SHA256SUMS"}
        assert (folder / "olist.dump").read_text().startswith("PGDMP fake dump of olist")
        digest = hashlib.sha256((folder / "olist.dump").read_bytes()).hexdigest()
        assert (folder / "SHA256SUMS").read_text() == f"{digest}  olist.dump\n"
        check = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=folder, capture_output=True, text=True)
        assert check.returncode == 0, check.stdout + check.stderr
        assert visible(dest) == {TS}
        assert not hidden_dirs(dest), f"Còn thư mục tạm: {hidden_dirs(dest)}"

    def test_m01_backup_permissions(self, ops, dest):
        assert self.run(ops, "-d", dest).returncode == 0
        assert stat.S_IMODE((dest / TS).stat().st_mode) == 0o700
        for path in (dest / TS).iterdir():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600, path.name

    def test_m01_backup_pg_dump_contract(self, ops, dest):
        result = self.run(ops, "-d", dest, PGPASSWORD="s3cr3t-pw")
        assert result.returncode == 0, result.stderr
        [call] = ops.pg_calls()
        argv = call["argv"]
        assert any(a in ("-Fc", "--format=custom", "--format=c", "-Fcustom") for a in argv) or (
            "-F" in argv and argv[argv.index("-F") + 1] in ("c", "custom")
        ), f"pg_dump phải dùng định dạng custom: {argv}"
        assert call["env"] == {"PGHOST": "127.0.0.1", "PGPORT": "25432", "PGUSER": "olist", "PGDATABASE": "olist",
                               "PGPASSWORD": "s3cr3t-pw"}
        assert not any("s3cr3t-pw" in a for a in argv), "Mật khẩu không được nằm trong tham số dòng lệnh"
        assert "s3cr3t-pw" not in result.stdout + result.stderr

    def test_m01_backup_connection_env(self, ops, dest):
        assert self.run(ops, "-d", dest / "a", OLIST_SHOP_PG_PORT="35432").returncode == 0
        assert self.run(ops, "-d", dest / "b", OLIST_SHOP_PG_PORT="35432", PGPORT="5555", PGHOST="db.internal",
                        PGUSER="backup", PGDATABASE="shop").returncode == 0
        first, second = (call["env"] for call in ops.pg_calls())
        assert first["PGPORT"] == "35432"
        assert (second["PGPORT"], second["PGHOST"], second["PGUSER"], second["PGDATABASE"]) == (
            "5555", "db.internal", "backup", "shop")

    def test_m01_backup_same_timestamp_is_skipped(self, ops, dest):
        assert self.run(ops, "-d", dest).returncode == 0
        dump = dest / TS / "olist.dump"
        before = (dump.read_bytes(), dump.stat().st_mtime_ns)
        result = self.run(ops, "-d", dest)
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"skip {dest}/{TS}\n"
        assert len(ops.pg_calls()) == 1
        assert (dump.read_bytes(), dump.stat().st_mtime_ns) == before

    @pytest.mark.parametrize("damage", ["dump", "sums"])
    def test_m01_backup_damaged_backup_is_rebuilt(self, ops, dest, damage):
        assert self.run(ops, "-d", dest).returncode == 0
        if damage == "dump":
            (dest / TS / "olist.dump").write_text("PGDMP truncated")
        else:
            (dest / TS / "SHA256SUMS").unlink()
        result = self.run(ops, "-d", dest)
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"created {dest}/{TS}\n"
        assert len(ops.pg_calls()) == 2
        check = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=dest / TS, capture_output=True, text=True)
        assert check.returncode == 0, check.stdout + check.stderr

    @pytest.mark.parametrize("mode", ["fail", "empty"])
    def test_m01_backup_failure_changes_nothing(self, ops, dest, mode):
        seed_backups(dest, OLD)
        (dest / "notes.txt").write_text("giữ")
        before = visible(dest)
        result = self.run(ops, "-k", 2, "-d", dest, FAKE_PG_MODE=mode)
        assert result.returncode == 1, result.stdout + result.stderr
        assert result.stdout == ""
        assert result.stderr.strip()
        assert visible(dest) == before, "Lỗi thì không tạo thư mục mới và không áp retention"
        assert not hidden_dirs(dest), f"Còn thư mục tạm: {hidden_dirs(dest)}"

    def test_m01_backup_retention(self, ops, dest):
        seed_backups(dest, OLD)
        (dest / "notes.txt").write_text("giữ")
        (dest / "manual-before-upgrade").mkdir()
        (dest / "manual-before-upgrade" / "olist.dump").write_text("giữ")
        result = self.run(ops, "-k", 3, "-d", dest)
        assert result.returncode == 0, result.stderr
        assert visible(dest) == {TS, OLD[-1], OLD[-2], "notes.txt", "manual-before-upgrade"}
        assert (dest / "manual-before-upgrade" / "olist.dump").read_text() == "giữ"

    def test_m01_backup_default_retention_is_five(self, ops, dest):
        seed_backups(dest, OLD)
        assert self.run(ops, "-d", dest).returncode == 0
        assert visible(dest) == {TS, *OLD[-4:]}

    def test_m01_backup_retention_from_env(self, ops, dest):
        seed_backups(dest, OLD)
        assert self.run(ops, "-d", dest, OLIST_BACKUP_KEEP="2").returncode == 0
        assert visible(dest) == {TS, OLD[-1]}

    def test_m01_backup_removes_stale_temp_dirs(self, ops, dest):
        stale = dest / ".inprogress-20261031T000000Z.abc123"
        stale.mkdir(parents=True)
        (stale / "olist.dump").write_text("PGDMP partial")
        result = self.run(ops, "-d", dest)
        assert result.returncode == 0, result.stderr
        assert not stale.exists(), "Thư mục .inprogress-* còn sót từ lần chạy bị ngắt phải được dọn"

    def test_m01_backup_default_destination(self, ops, tmp_path, dest):
        result = self.run(ops)
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"created backups/{TS}\n"
        assert (tmp_path / "backups" / TS / "olist.dump").is_file()
        result = self.run(ops, OLIST_BACKUP_DIR=str(dest))
        assert result.returncode == 0, result.stderr
        assert result.stdout == f"created {dest}/{TS}\n"

    @pytest.mark.parametrize("args", [("-k", "0"), ("-k", "x"), ("-k",), ("-z",), ("extra",), ("-d", "")])
    def test_m01_backup_usage_errors(self, ops, args):
        result = self.run(ops, *args)
        assert result.returncode == 2, result.stdout + result.stderr
        assert result.stderr.startswith("Usage:")
        assert ops.pg_calls() == []

    @pytest.mark.parametrize("stamp", ["2026-11-01", "20261101T020000", "20261101T020000Z/../../x", "yesterday"])
    def test_m01_backup_bad_timestamp(self, ops, dest, stamp):
        result = self.run(ops, "-d", dest, BACKUP_TIMESTAMP=stamp)
        assert result.returncode == 2, result.stdout + result.stderr
        assert result.stderr.strip()
        assert ops.pg_calls() == []

    def test_m01_backup_lock(self, ops, dest):
        first = ops.popen("backup.sh", "-d", dest, env={"BACKUP_TIMESTAMP": TS, "FAKE_PG_MODE": "slow"})
        try:
            deadline = time.monotonic() + 20
            while not ops.started.exists():
                assert first.poll() is None, first.communicate()
                assert time.monotonic() < deadline, "pg_dump giả không khởi động được"
                time.sleep(0.05)
            second = self.run(ops, "-d", dest)
            assert second.returncode == 75, second.stdout + second.stderr
            assert second.stderr.strip()
            assert second.elapsed < 10, "Đang có bản khác chạy thì thoát ngay, không chờ khoá"
            assert not (dest / TS).exists()
        finally:
            if first.poll() is None:
                os.killpg(first.pid, signal.SIGKILL)
            first.communicate(timeout=20)
        third = self.run(ops, "-d", dest)
        assert third.returncode == 0, "Tiến trình giữ khoá đã chết thì khoá phải được nhả (flock trên fd)"

    def test_m01_backup_sigterm_cleans_up(self, ops, dest):
        result = self.run(ops, "-d", dest, FAKE_PG_MODE="selfterm")
        assert result.returncode != 0
        assert result.stdout == ""
        assert not (dest / TS).exists()
        assert not hidden_dirs(dest), f"Còn thư mục tạm: {hidden_dirs(dest)}"
        again = self.run(ops, "-d", dest)
        assert again.returncode == 0, again.stderr
        assert again.stdout == f"created {dest}/{TS}\n"


@pytest.mark.parametrize("name", OPS)
def test_m01_shellcheck_clean(project_root, name):
    script = require_file(project_root / "ops" / name)
    Exercise.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


@pytest.mark.usefixtures("healthcheck_tools", "backup_tools")
def test_m01_checks_catch_defective_scripts(tmp_path, api):
    """Bản lỗi trong fixtures/defective/ops: curl không -f, down -v rồi ghi đè .env, pg_dump thẳng vào thư mục đích."""
    defective = Ops(tmp_path, FIXTURES / "defective")
    health = healthcheck_problems(defective, api)
    assert any("failing=redis" in p for p in health), health
    boot = bootstrap_problems(defective, api)
    assert any("ghi đè" in p for p in boot), boot
    assert any("phá huỷ" in p for p in boot), boot
    assert any("chờ" in p for p in boot), boot
    backup = backup_problems(defective)
    assert any("pg_dump lỗi" in p for p in backup), backup
    assert any("notes.txt" in p for p in backup), backup
    assert any("skip" in p for p in backup), backup


INTEGRATION = "DEVOPS_CAPSTONE_INTEGRATION"


def test_m01_integration_real_stack(tmp_path, project_root):
    """Tuỳ chọn: chạy healthcheck.sh và backup.sh với Postgres, Redis và API thật dựng bằng DockerLab."""
    if os.environ.get(INTEGRATION) != "1":
        pytest.skip(f"Test tích hợp tuỳ chọn, chỉ chạy khi đặt {INTEGRATION}=1 (cần Docker, image olist-shop:dev, "
                    "postgres:16, redis:7 và pg_dump 16 trên máy)")
    ops = Ops(tmp_path, project_root)
    health, backup = ops.script("healthcheck.sh"), ops.script("backup.sh")
    for image in ("postgres:16", "redis:7", "olist-shop:dev"):
        Exercise.require_image(image)
    Exercise.require_tool("pg_dump", min_version="16")
    Exercise.require_tool("pg_restore", min_version="16")
    real_path = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    with DockerLab() as lab:
        lab.start("postgres", "postgres:16", ports=[5432], memory="512m",
                  env={"POSTGRES_USER": "olist", "POSTGRES_PASSWORD": "olist", "POSTGRES_DB": "olist"})
        lab.start("redis", "redis:7")
        deadline = time.monotonic() + 90
        while lab.exec("postgres", "pg_isready", "-h", "127.0.0.1", "-U", "olist", "-d", "olist").returncode != 0:
            assert time.monotonic() < deadline, f"Postgres không sẵn sàng:\n{lab.logs('postgres')[-2000:]}"
            time.sleep(0.5)
        lab.wait_log("redis", "Ready to accept connections")
        lab.start("api", "olist-shop:dev", ports=[8000], env={
            "DATABASE_URL": "postgresql+psycopg://olist:olist@postgres:5432/olist",
            "REDIS_URL": "redis://redis:6379/0",
        })
        url = f"http://127.0.0.1:{lab.port('api', 8000)}"
        lab.wait_http("api", url + "/healthz")
        ok = ops.run("healthcheck.sh", "-u", url, "-w", 60, env=real_path, script=health)
        assert (ok.returncode, ok.stdout) == (0, "OK db=ok redis=ok\n"), ok.stdout + ok.stderr
        dest = tmp_path / "backups"
        made = ops.run("backup.sh", "-d", dest, env={**real_path, "PGPORT": lab.port("postgres", 5432),
                                                     "PGPASSWORD": "olist", "BACKUP_TIMESTAMP": TS}, script=backup)
        assert made.returncode == 0, made.stderr
        listing = subprocess.run(["pg_restore", "--list", str(dest / TS / "olist.dump")], capture_output=True, text=True)
        assert listing.returncode == 0 and "TABLE" in listing.stdout, listing.stderr
        lab.exec("redis", "redis-cli", "shutdown", "nosave")
        down = ops.run("healthcheck.sh", "-u", url, env=real_path, script=health)
        assert down.returncode == 1, down.stdout + down.stderr
        assert down.stdout == "FAIL readyz=503 failing=redis\n"
