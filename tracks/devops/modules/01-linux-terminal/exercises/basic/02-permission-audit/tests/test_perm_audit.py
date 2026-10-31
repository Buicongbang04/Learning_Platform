import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Cần bash")


def run(*args):
    env = {**os.environ, "LC_ALL": "C"}
    return subprocess.run(
        [BASH, str(ex.path("perm_audit.sh")), *map(str, args)], capture_output=True, text=True, timeout=30, env=env
    )


def make(root: Path, rel: str, mode: int, content: str = "x\n") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)
    return path


def make_dir(root: Path, rel: str, mode: int) -> Path:
    path = root / rel
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode)
    return path


@pytest.fixture
def release(tmp_path):
    root = tmp_path / "olist shop"
    make(root, "app/main.py", 0o644)
    make(root, "app/run.sh", 0o755)
    make(root, "app/upload cache/report.csv", 0o666)
    make(root, "bin/olist-admin", 0o4755)
    make(root, "bin/olist-report", 0o2755)
    make(root, "config/.env", 0o644)
    make(root, "config/.env.example", 0o644)
    make(root, "config/tls/server.key", 0o640)
    make(root, "config/tls/server.crt", 0o644)
    make(root, "config/tls/ca.pem", 0o644)
    make(root, "deploy/id_ed25519", 0o600)
    make(root, "deploy/id_ed25519.pub", 0o644)
    make(root, "deploy/id_rsa", 0o644)
    make_dir(root, "shared", 0o777)
    make_dir(root, "tmp", 0o1777)
    make(root, "tmp/session.lock", 0o600)
    return root


def test_usage_without_args():
    result = run()
    assert result.returncode == 2
    assert result.stderr.startswith("Usage:")
    assert result.stdout == ""


def test_missing_dir(tmp_path):
    result = run(tmp_path / "khong-co")
    assert result.returncode == 2
    assert result.stderr.strip()
    assert result.stdout == ""


def test_findings_on_release_tree(release):
    result = run(release)
    assert result.returncode == 1, result.stderr
    assert result.stdout.splitlines() == [
        "env-readable config/.env",
        "key-too-open config/tls/server.key",
        "key-too-open deploy/id_rsa",
        "setgid bin/olist-report",
        "setuid bin/olist-admin",
        "world-writable app/upload cache/report.csv",
        "world-writable-dir shared",
    ]


def test_clean_tree_exits_zero(tmp_path):
    root = tmp_path / "clean"
    make(root, "app.py", 0o644)
    make(root, "secrets/.env", 0o600)
    make(root, "secrets/db.key", 0o600)
    make_dir(root, "tmp", 0o1777)
    result = run(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_tree_is_not_modified(release):
    before = {p: stat.S_IMODE(p.lstat().st_mode) for p in release.rglob("*")}
    run(release)
    assert {p: stat.S_IMODE(p.lstat().st_mode) for p in release.rglob("*")} == before


def test_relative_dir_argument(release):
    result = subprocess.run(
        [BASH, str(ex.path("perm_audit.sh")), "."],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "LC_ALL": "C"},
        cwd=release,
    )
    assert result.returncode == 1, result.stderr
    assert "setuid bin/olist-admin" in result.stdout.splitlines()
    assert not any(line.split(" ", 1)[1].startswith(("./", "/")) for line in result.stdout.splitlines())


def test_symlink_to_open_file_not_followed(tmp_path):
    root = tmp_path / "links"
    outside = make(tmp_path / "outside", "shared.txt", 0o666)
    root.mkdir()
    (root / "link.txt").symlink_to(outside)
    result = run(root)
    assert result.returncode == 0, result.stdout
    assert result.stdout == ""
