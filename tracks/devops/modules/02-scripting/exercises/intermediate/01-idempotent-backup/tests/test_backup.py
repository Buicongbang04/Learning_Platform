import hashlib
import json
import os
import shutil
import signal
import sys
import stat
import subprocess
import time
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed, sandbox_command

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Cần bash")
DATE = "2026-11-01"
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
"$FAKE_PYTHON" - "$FAKE_LOG" "$@" <<'PY'
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
DUMP_NAME = "olist-{}.dump"


@pytest.fixture(autouse=True)
def tools():
    ex.require_tool("flock")
    ex.require_tool("sha256sum")


class Harness:
    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        fake = self.bin / "pg_dump"
        fake.write_text(FAKE_PG_DUMP)
        fake.chmod(0o755)
        self.log = tmp_path / "pg_dump.jsonl"
        self.started = tmp_path / "started"
        self.dir = tmp_path / "my backups" / "olist"

    def env(self, mode="ok", date=DATE, extra=None):
        env = dict(
            PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            FAKE_LOG=str(self.log),
            FAKE_PG_MODE=mode,
            FAKE_STARTED=str(self.started),
            FAKE_PYTHON=sys.executable,
            BACKUP_DATE=date,
        )
        env.update(extra or {})
        return env

    def cmd(self, *args):
        return [BASH, str(ex.path("backup.sh")), *map(str, args)]

    def run(self, *args, mode="ok", date=DATE, extra=None, raw=False):
        args = args if (args or raw) else (self.dir,)
        return run_sandboxed(self.cmd(*args), writable=[self.tmp], cwd=self.tmp, env=self.env(mode, date, extra), timeout=60)

    def popen(self, *args, mode="ok"):
        argv = sandbox_command(self.cmd(*args), writable=[self.tmp], cwd=self.tmp, env=self.env(mode))
        return subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env={}, start_new_session=True)

    def calls(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def names(self) -> set[str]:
        return {p.name for p in self.dir.iterdir()} if self.dir.exists() else set()

    def seed(self, dates):
        self.dir.mkdir(parents=True, exist_ok=True)
        for d in dates:
            dump = self.dir / DUMP_NAME.format(d)
            dump.write_text(f"PGDMP old {d}")
            digest = hashlib.sha256(dump.read_bytes()).hexdigest()
            (self.dir / f"{dump.name}.sha256").write_text(f"{digest}  {dump.name}\n")


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def allowed(names: set[str]) -> bool:
    return all(n == ".backup.lock" or (n.startswith("olist-") and not n.startswith(".")) or n == "notes.txt" for n in names)


def test_creates_backup_with_checksum(h):
    result = h.run()
    assert result.returncode == 0, result.stderr
    dump = h.dir / DUMP_NAME.format(DATE)
    assert result.stdout == f"created {dump}\n"
    assert dump.read_text().startswith("PGDMP fake dump of olist")
    expected = f"{hashlib.sha256(dump.read_bytes()).hexdigest()}  {dump.name}\n"
    assert (h.dir / f"{dump.name}.sha256").read_text() == expected
    check = subprocess.run(["sha256sum", "-c", f"{dump.name}.sha256"], cwd=h.dir, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    assert h.names() <= {dump.name, f"{dump.name}.sha256", ".backup.lock"}


def test_permissions(h):
    assert h.run().returncode == 0
    assert stat.S_IMODE(h.dir.stat().st_mode) == 0o700
    for p in h.dir.glob("olist-*"):
        assert stat.S_IMODE(p.stat().st_mode) == 0o600, p.name


def test_pg_dump_contract(h):
    result = h.run(extra={"PGPASSWORD": "s3cr3t-pw"})
    assert result.returncode == 0, result.stderr
    [call] = h.calls()
    argv = call["argv"]
    assert any(a in ("-Fc", "--format=custom", "--format=c", "-Fcustom") for a in argv) or (
        "-F" in argv and argv[argv.index("-F") + 1] in ("c", "custom")
    ), f"pg_dump phải dùng định dạng custom: {argv}"
    assert call["env"] == {"PGHOST": "localhost", "PGPORT": "25432", "PGUSER": "olist", "PGDATABASE": "olist", "PGPASSWORD": "s3cr3t-pw"}
    assert not any("s3cr3t-pw" in a for a in argv), "Mật khẩu không được nằm trong tham số dòng lệnh"
    assert "s3cr3t-pw" not in result.stdout + result.stderr


def test_connection_env_overrides(h):
    result = h.run(extra={"PGHOST": "db.internal", "PGPORT": "5433", "PGUSER": "backup", "PGDATABASE": "shop"})
    assert result.returncode == 0, result.stderr
    assert h.calls()[0]["env"]["PGHOST"] == "db.internal"
    assert h.calls()[0]["env"]["PGDATABASE"] == "shop"


def test_second_run_same_day_is_skipped(h):
    assert h.run().returncode == 0
    dump = h.dir / DUMP_NAME.format(DATE)
    before = (dump.read_bytes(), dump.stat().st_mtime_ns)
    result = h.run()
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"skip {dump}\n"
    assert len(h.calls()) == 1, "Đã có bản sao lưu hợp lệ của ngày này thì không gọi pg_dump lần nữa"
    assert (dump.read_bytes(), dump.stat().st_mtime_ns) == before


@pytest.mark.parametrize("damage", ["checksum", "missing-checksum"])
def test_damaged_backup_is_recreated(h, damage):
    assert h.run().returncode == 0
    dump = h.dir / DUMP_NAME.format(DATE)
    sums = h.dir / f"{dump.name}.sha256"
    if damage == "checksum":
        dump.write_text("PGDMP truncated")
    else:
        sums.unlink()
    result = h.run()
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"created {dump}\n"
    assert len(h.calls()) == 2
    assert sums.read_text() == f"{hashlib.sha256(dump.read_bytes()).hexdigest()}  {dump.name}\n"


def test_failure_leaves_no_partial_and_keeps_old_backups(h):
    h.seed([f"2026-10-{d:02d}" for d in range(1, 11)])
    (h.dir / "notes.txt").write_text("giữ")
    before = h.names()
    result = h.run("-k", 2, h.dir, mode="fail")
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip()
    assert h.names() - {".backup.lock"} == before - {".backup.lock"}, "Lỗi thì không tạo gì mới và không áp retention"


def test_empty_dump_is_failure(h):
    result = h.run(mode="empty")
    assert result.returncode == 1
    assert not (h.dir / DUMP_NAME.format(DATE)).exists()
    assert allowed(h.names())
    assert not [n for n in h.names() if n.startswith(".") and n != ".backup.lock"]


def test_retention_keeps_newest_and_ignores_other_files(h):
    h.seed([f"2026-10-{d:02d}" for d in range(1, 11)])
    (h.dir / "notes.txt").write_text("giữ")
    (h.dir / "olist-manual.dump").write_text("giữ")
    result = h.run("-k", 3, h.dir)
    assert result.returncode == 0, result.stderr
    kept = {DUMP_NAME.format(d) for d in (DATE, "2026-10-10", "2026-10-09")}
    assert h.names() - {".backup.lock"} == kept | {f"{n}.sha256" for n in kept} | {"notes.txt", "olist-manual.dump"}


def test_default_retention_is_seven(h):
    h.seed([f"2026-10-{d:02d}" for d in range(1, 11)])
    assert h.run().returncode == 0
    assert len([n for n in h.names() if n.endswith(".dump")]) == 7


@pytest.mark.parametrize("args", [(), ("-k", 0, "{dir}"), ("-k", "x", "{dir}"), ("-z", "{dir}"), ("{dir}", "extra")])
def test_usage_errors(h, args):
    result = h.run(*(str(a).format(dir=h.dir) for a in args), raw=True)
    assert result.returncode == 2
    assert result.stderr.startswith("Usage:")
    assert h.calls() == []


@pytest.mark.parametrize("date", ["2026-11-1", "yesterday", "2026-11-01/../../x"])
def test_bad_backup_date(h, date):
    result = h.run(date=date)
    assert result.returncode == 2
    assert result.stderr.strip()
    assert h.calls() == []


def wait_for(path: Path, proc: subprocess.Popen, seconds=20):
    deadline = time.monotonic() + seconds
    while not path.exists():
        assert proc.poll() is None, proc.communicate()
        assert time.monotonic() < deadline, "pg_dump giả không khởi động được"
        time.sleep(0.05)


def test_lock_held_by_running_backup(h):
    first = h.popen(h.dir, mode="slow")
    try:
        wait_for(h.started, first)
        start = time.monotonic()
        second = h.run()
        assert second.returncode == 75, second.stdout + second.stderr
        assert second.stderr.strip()
        assert time.monotonic() - start < 10, "Đang có bản khác chạy thì thoát ngay, không chờ khoá"
        assert not (h.dir / DUMP_NAME.format(DATE)).exists()
    finally:
        if first.poll() is None:
            os.killpg(first.pid, signal.SIGKILL)
        first.communicate(timeout=20)
    third = h.run()
    assert third.returncode == 0, "Tiến trình giữ khoá đã chết thì khoá phải được nhả (flock trên fd)"


def test_sigterm_cleans_up(h):
    """pg_dump giả gửi SIGTERM cho cả process group của nó (như systemd hay Ctrl+C), bên trong sandbox."""
    result = h.run(mode="selfterm")
    assert result.returncode != 0
    assert result.stdout == ""
    assert not (h.dir / DUMP_NAME.format(DATE)).exists()
    assert not [n for n in h.names() if n.startswith(".") and n != ".backup.lock"], f"Còn tệp tạm: {h.names()}"
    again = h.run()
    assert again.returncode == 0, again.stderr
    assert again.stdout == f"created {h.dir / DUMP_NAME.format(DATE)}\n"


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(ex.path("backup.sh"))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
