import os
import re
import shlex
import sys
import time
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
CHECKER = """
import os, sys, pathlib, time
pathlib.Path(sys.argv[1]).open("a").write(f"{os.getcwd()}|{os.environ.get('RELEASE_VERSION')}\\n")
if len(sys.argv) > 2 and sys.argv[2] == "slow":
    time.sleep(20)
sys.exit(0 if pathlib.Path("HEALTH").read_text().strip() == "ok" else 1)
"""


class Harness:
    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.root = tmp_path / "srv" / "olist shop"
        self.checker = tmp_path / "checker.py"
        self.checker.write_text(CHECKER)
        self.check_log = tmp_path / "checks.log"

    def build(self, name: str, health: str = "ok") -> Path:
        src = self.tmp / "builds" / name
        (src / "app").mkdir(parents=True, exist_ok=True)
        (src / "app" / "main.py").write_text(f"VERSION = {name!r}\n")
        (src / "HEALTH").write_text(health)
        return src

    def check(self, *extra: str) -> str:
        return shlex.join([sys.executable, str(self.checker), str(self.check_log), *extra])

    def run(self, *args, timeout=60):
        return run_sandboxed(
            [sys.executable, ex.path("release.py"), "--root", self.root, *map(str, args)],
            writable=[self.tmp],
            cwd=self.tmp,
            env={},
            timeout=timeout,
        )

    def deploy(self, version: str, *extra, health="ok"):
        return self.run("deploy", self.build(version, health), "--version", version, *extra)

    def current(self) -> str | None:
        link = self.root / "current"
        return os.readlink(link) if link.is_symlink() else None

    def history(self) -> list[str]:
        path = self.root / ".history"
        return path.read_text().split() if path.exists() else []

    def snapshot(self) -> list[tuple[str, str | None]]:
        if not self.root.exists():
            return []
        return sorted(
            (p.relative_to(self.root).as_posix(), os.readlink(p) if p.is_symlink() else None) for p in self.root.rglob("*")
        )


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def test_first_deploy(h):
    result = h.deploy("v1.0.0")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr.strip(), "Ghi log ra stderr"
    assert h.current() == "releases/v1.0.0", "current là symlink tương đối tới releases/<version>"
    assert (h.root / "current" / "app" / "main.py").read_text() == "VERSION = 'v1.0.0'\n"
    assert h.history() == ["v1.0.0"]
    assert sorted(p.name for p in h.root.iterdir()) == [".history", "current", "releases"]
    assert sorted(p.name for p in (h.root / "releases").iterdir()) == ["v1.0.0"]


def test_status(h):
    result = h.run("status")
    assert result.returncode == 1
    assert result.stdout == ""
    h.deploy("v1")
    result = h.run("status")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "v1\n"


def test_redeploy_current_is_noop(h):
    assert h.deploy("v1", "--check", h.check()).returncode == 0
    before = h.snapshot()
    checks = h.check_log.read_text()
    result = h.deploy("v1", "--check", h.check())
    assert result.returncode == 0, result.stderr
    assert h.snapshot() == before
    assert h.history() == ["v1"]
    assert h.check_log.read_text() == checks, "Bản đang chạy rồi thì không chạy lại check"


def test_switch_and_rollback(h):
    for v in ("v1", "v2", "v3"):
        assert h.deploy(v).returncode == 0
    assert h.current() == "releases/v3"
    assert h.history() == ["v1", "v2", "v3"]
    assert h.run("rollback").returncode == 0
    assert h.current() == "releases/v2"
    assert h.history() == ["v1", "v2"]
    assert h.run("rollback").returncode == 0
    assert h.current() == "releases/v1"
    result = h.run("rollback")
    assert result.returncode == 1
    assert result.stderr.strip()
    assert h.current() == "releases/v1"
    assert sorted(p.name for p in (h.root / "releases").iterdir()) == ["v1", "v2", "v3"]


def test_existing_release_is_reused_not_recopied(h):
    h.deploy("v1")
    h.deploy("v2")
    marker = h.root / "releases" / "v1" / "uploaded-by-app.txt"
    marker.write_text("x")
    result = h.run("deploy", h.build("v1-other-source"), "--version", "v1")
    assert result.returncode == 0, result.stderr
    assert h.current() == "releases/v1"
    assert marker.exists()
    assert (h.root / "releases" / "v1" / "app" / "main.py").read_text() == "VERSION = 'v1'\n"
    assert h.history() == ["v1", "v2", "v1"]


def test_check_runs_in_new_release_with_version_env(h):
    result = h.deploy("v1", "--check", h.check())
    assert result.returncode == 0, result.stderr
    cwd, version = h.check_log.read_text().strip().split("|")
    assert Path(cwd).resolve() == (h.root / "releases" / "v1").resolve()
    assert version == "v1"


def test_failed_check_rolls_back(h):
    assert h.deploy("v1").returncode == 0
    result = h.deploy("v2", "--check", h.check(), health="broken")
    assert result.returncode == 1
    assert result.stderr.strip()
    assert h.current() == "releases/v1"
    assert h.history() == ["v1"]


def test_failed_check_on_first_deploy_leaves_no_current(h):
    result = h.deploy("v1", "--check", h.check(), health="broken")
    assert result.returncode == 1
    assert h.current() is None
    assert not (h.root / "current").exists()
    assert h.history() == []


def test_check_timeout_rolls_back(h):
    assert h.deploy("v1").returncode == 0
    start = time.monotonic()
    result = h.deploy("v2", "--check", h.check("slow"), "--check-timeout", 1)
    assert result.returncode == 1
    assert time.monotonic() - start < 15
    assert h.current() == "releases/v1"


def test_missing_check_command_rolls_back(h):
    assert h.deploy("v1").returncode == 0
    result = h.deploy("v2", "--check", str(h.tmp / "khong-co-lenh"))
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert h.current() == "releases/v1"


def test_check_is_not_run_through_a_shell(h):
    pwned = h.tmp / "pwned"
    check = h.check() + f" ; touch {shlex.quote(str(pwned))}"
    h.deploy("v1", "--check", check)
    assert not pwned.exists(), "--check phải tách bằng shlex và chạy không qua shell"


def test_no_shell_true_in_source():
    assert not re.search(r"shell\s*=\s*True", ex.read("release.py")), "Không dùng shell=True"
    assert "os.system(" not in ex.read("release.py")


def test_dry_run_changes_nothing(h):
    h.deploy("v1")
    before = h.snapshot()
    result = h.run("deploy", h.build("v2"), "--version", "v2", "--dry-run", "--check", h.check())
    assert result.returncode == 0, result.stderr
    assert result.stderr.strip()
    assert h.snapshot() == before
    assert not h.check_log.exists()
    for v in ("v2",):
        h.deploy(v)
    before = h.snapshot()
    assert h.run("rollback", "--dry-run").returncode == 0
    assert h.snapshot() == before


@pytest.mark.parametrize("version", ["../evil", "v1/../../x", ".", "..", "", "v 1", "-rf", ".hidden"])
def test_bad_version_rejected(h, version):
    result = h.run("deploy", h.build("ok"), "--version", version)
    assert result.returncode == 2
    assert not (h.root / "releases").exists() or not any((h.root / "releases").iterdir())
    assert not (h.tmp / "evil").exists() and not (h.tmp / "x").exists()


def test_missing_source(h):
    result = h.run("deploy", h.tmp / "khong-co", "--version", "v1")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert h.current() is None


def test_usage_errors(h):
    assert h.run().returncode == 2
    assert h.run("deploy").returncode == 2
    assert h.run("explode").returncode == 2


def test_no_temp_leftovers(h):
    h.deploy("v1")
    h.deploy("v2", "--check", h.check(), health="broken")
    h.deploy("v3")
    h.run("rollback")
    names = sorted(p.name for p in h.root.iterdir())
    assert names == [".history", "current", "releases"]
    assert sorted(p.name for p in (h.root / "releases").iterdir()) == ["v1", "v2", "v3"]
