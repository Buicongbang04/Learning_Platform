import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
RUN_TIMEOUT = 30
DELAY = 1.5


class Audit:
    def __init__(self, mode: str, token: str) -> None:
        self.mode = mode
        self.token = token
        self.requests: list[dict] = []
        audit = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                audit.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                time.sleep(DELAY)
                if audit.mode == "drop":
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                status, payload = {
                    "ok": (201, {"id": secrets.token_hex(4)}),
                    "unauthorized": (401, {"error": f"invalid token {audit.token}"}),
                    "error": (500, {"error": f"upstream timeout; request had Authorization: Bearer {audit.token}"}),
                }[audit.mode]
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/reports"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "Audit":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()


def closed_port_url() -> str:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/api/reports"


class Watch:
    """Quét /proc của mọi tiến trình trong lúc script chạy: secret không được nằm trong cmdline hay environ."""

    def __init__(self, secret: str, active: bool = True) -> None:
        self.secret = secret.encode()
        self.active = active
        self.leaks: list[str] = []
        self.seen_script = False
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)

    def scan(self) -> None:
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit() or int(proc.name) == os.getpid():
                continue
            for name in ("cmdline", "environ"):
                try:
                    data = (proc / name).read_bytes()
                except OSError:
                    continue
                if name == "cmdline" and b"push_report.py" in data:
                    self.seen_script = True
                if self.secret in data:
                    shown = data.replace(b"\0", b" ").replace(self.secret, b"<SECRET>")[:200]
                    self.leaks.append(f"/proc/{proc.name}/{name}: {shown.decode(errors='replace')}")

    def loop(self) -> None:
        while not self.stop.is_set():
            self.scan()
            time.sleep(0.05)

    def __enter__(self) -> "Watch":
        if self.active:
            self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop.set()
        if self.active:
            self.thread.join()


class Lab:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.work = root / "work"
        self.work.mkdir()
        self.token = "tok_" + secrets.token_urlsafe(24)
        self.secret_file = root / "secrets" / "audit-token"
        self.secret_file.parent.mkdir()
        self.secret_file.write_text(self.token + "\n")
        self.secret_file.chmod(0o600)
        self.report = self.work / "sync-report.json"
        self.report.write_text(json.dumps({"added": ["Pháp chế/NDA-01.txt"], "updated": [], "deleted": [],
                                           "errors": [], "run": secrets.token_hex(4)}, ensure_ascii=False))

    def run(self, env: dict[str, str], *, watch_procs: bool = True) -> tuple[subprocess.CompletedProcess, Watch]:
        cmd = [sys.executable, str(ex.path("push_report.py")), str(self.report)]
        with Watch(self.token, active=watch_procs) as watch:
            try:
                done = run_sandboxed(cmd, writable=[self.root], cwd=self.work, env=env, timeout=RUN_TIMEOUT)
            except subprocess.TimeoutExpired:
                pytest.fail(f"push_report.py chạy quá {RUN_TIMEOUT} s")
        return done, watch

    def assert_no_leak(self, done: subprocess.CompletedProcess, watch: Watch, label: str) -> None:
        assert not watch.leaks, f"{label}: secret lộ qua tiến trình:\n" + "\n".join(watch.leaks[:5])
        for stream, text in (("stdout", done.stdout), ("stderr", done.stderr)):
            assert self.token not in text, f"{label}: secret lộ trong {stream}:\n{text[-1500:]}"
        for path in self.work.rglob("*"):
            if path.is_file():
                assert self.token.encode() not in path.read_bytes(), f"{label}: secret lộ trong tệp {path.name}"
        assert "Traceback" not in done.stderr, f"{label}: lỗi phải báo bằng thông báo, không phải traceback:\n" \
                                               f"{done.stderr[-1500:]}"


@pytest.fixture
def lab(tmp_path):
    return Lab(tmp_path)


def test_success_sends_token_from_file(lab):
    with Audit("ok", lab.token) as audit:
        done, watch = lab.run({"AUDIT_URL": audit.url, "AUDIT_TOKEN_FILE": str(lab.secret_file)})
    assert watch.seen_script, "Test không quan sát được tiến trình của script trong /proc (môi trường lạ?)"
    assert done.returncode == 0, f"Gửi thành công phải thoát 0, thoát {done.returncode}\n{done.stderr[-1500:]}"
    assert len(audit.requests) == 1, f"Cần đúng 1 request tới dịch vụ audit, nhận {len(audit.requests)}"
    request = audit.requests[0]
    assert request["path"] == "/api/reports", f"Request phải tới đúng AUDIT_URL, tới {request['path']}"
    assert request["auth"] == f"Bearer {lab.token}", "Header Authorization phải là 'Bearer <token trong tệp>'"
    assert request["body"] == lab.report.read_bytes(), "Thân request phải là nguyên nội dung tệp báo cáo"
    assert (lab.work / "push_report.log").is_file(), "Script phải ghi log vào push_report.log trong thư mục làm việc"
    lab.assert_no_leak(done, watch, "Gửi thành công")


@pytest.mark.parametrize("mode", ["unauthorized", "error", "drop", "refused"])
def test_send_failures_do_not_leak(lab, mode):
    if mode == "refused":
        done, watch = lab.run({"AUDIT_URL": closed_port_url(), "AUDIT_TOKEN_FILE": str(lab.secret_file)})
    else:
        with Audit(mode, lab.token) as audit:
            done, watch = lab.run({"AUDIT_URL": audit.url, "AUDIT_TOKEN_FILE": str(lab.secret_file)})
        assert len(audit.requests) == 1, f"{mode}: cần đúng 1 request (không thử lại), nhận {len(audit.requests)}"
    assert done.returncode == 1, f"{mode}: gửi thất bại phải thoát 1, thoát {done.returncode}\n{done.stderr[-1500:]}"
    assert done.stderr.strip(), f"{mode}: phải có thông báo lỗi trên stderr"
    lab.assert_no_leak(done, watch, mode)


def test_config_errors(lab):
    with Audit("ok", lab.token) as audit:
        cases = []
        missing = {"AUDIT_URL": audit.url}
        cases.append(("thiếu AUDIT_TOKEN_FILE", missing, True))
        cases.append(("AUDIT_TOKEN_FILE trỏ tệp không có", missing | {"AUDIT_TOKEN_FILE": str(lab.root / "nope")}, True))
        empty = lab.root / "secrets" / "empty"
        empty.write_text("\n")
        empty.chmod(0o600)
        cases.append(("tệp token rỗng", missing | {"AUDIT_TOKEN_FILE": str(empty)}, True))
        cases.append(("chỉ có AUDIT_TOKEN trong env", missing | {"AUDIT_TOKEN": lab.token}, False))
        cases.append(("AUDIT_TOKEN_FILE hợp lệ nhưng có cả AUDIT_TOKEN trong env",
                      missing | {"AUDIT_TOKEN_FILE": str(lab.secret_file), "AUDIT_TOKEN": lab.token}, False))
        for label, env, watch_procs in cases:
            done, watch = lab.run(env, watch_procs=watch_procs)
            assert done.returncode == 2, f"{label}: phải thoát 2, thoát {done.returncode}\n{done.stderr[-1500:]}"
            lab.assert_no_leak(done, watch, label)
        lab.secret_file.chmod(0o644)
        done, watch = lab.run(missing | {"AUDIT_TOKEN_FILE": str(lab.secret_file)})
        assert done.returncode == 2, f"tệp token đọc được bởi group/other (0644): phải thoát 2, thoát {done.returncode}"
        lab.assert_no_leak(done, watch, "tệp token 0644")
    assert audit.requests == [], f"Lỗi cấu hình thì không được gửi request nào, đã gửi {len(audit.requests)}"
