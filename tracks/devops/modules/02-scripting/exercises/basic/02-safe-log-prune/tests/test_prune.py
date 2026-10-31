import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None or shutil.which("find") is None, reason="Cần bash và find")
DAY = 86400
ABSOLUTE_TOOLS = re.compile(r"(?<![\w-])(?:/usr)?/bin/(?:find|rm)\b|\bcommand\s+(?:find|rm)\b|\\(?:find|rm)\b")
FAKE_TOOL = """#!/usr/bin/env bash
printf '%s\\n' "$(basename "$0") $*" >> "$FAKE_LOG"
exit 0
"""


@pytest.fixture
def run(tmp_path):
    def runner(*args, env_extra=None):
        env = {"LC_ALL": "C", **(env_extra or {})}
        return run_sandboxed(
            [BASH, ex.path("prune.sh"), *map(str, args)], writable=[tmp_path], cwd=tmp_path, env=env, timeout=60
        )

    return runner


def make(path: Path, age_days: float, content: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    stamp = time.time() - age_days * DAY
    os.utime(path, (stamp, stamp))
    return path


@pytest.fixture
def logs(tmp_path):
    root = tmp_path / "var log" / "olist"
    old = [
        make(root / "api.log.3.gz", 30),
        make(root / "worker" / "worker.log.1", 9),
        make(root / "space name.log.2", 20),
        make(root / "-rf.log.4", 40),
        make(root / "boundary-over.log.5", 8.5),
    ]
    keep = [
        make(root / "api.log", 30),
        make(root / "api.log.1", 2),
        make(root / "boundary-under.log.6", 7.5),
        make(root / "notes.txt", 60),
    ]
    folder = root / "archive.log.d"
    folder.mkdir()
    stamp = time.time() - 50 * DAY
    os.utime(folder, (stamp, stamp))
    outside = make(tmp_path / "outside" / "secret.log.9", 90)
    link = root / "link.log.7"
    link.symlink_to(outside)
    os.utime(link, (stamp, stamp), follow_symlinks=False)
    return {"root": root, "old": old, "keep": keep + [outside], "dir": folder, "link": link}


def lines(text: str) -> set[str]:
    return set(text.splitlines())


def test_no_absolute_find_or_rm():
    source = ex.read("prune.sh")
    assert not ABSOLUTE_TOOLS.search(source), "Gọi find và rm qua PATH (test thay chúng bằng bản giả để biết script có quét thư mục nguy hiểm không)"


def test_deletes_only_old_rotated_files(logs, run):
    result = run("-d", logs["root"], "-a", 7)
    assert result.returncode == 0, result.stderr
    assert lines(result.stdout) == {f"deleted {p}" for p in logs["old"]}
    assert all(not p.exists() for p in logs["old"])
    assert all(p.exists() for p in logs["keep"])
    assert logs["dir"].is_dir()
    assert logs["link"].is_symlink()
    assert result.stderr.splitlines()[-1] == "total=5"


def test_dry_run_changes_nothing(logs, run):
    before = sorted(p.as_posix() for p in logs["root"].parent.parent.rglob("*"))
    result = run("-n", "-d", logs["root"], "-a", 7)
    assert result.returncode == 0, result.stderr
    assert lines(result.stdout) == {f"would delete {p}" for p in logs["old"]}
    assert sorted(p.as_posix() for p in logs["root"].parent.parent.rglob("*")) == before
    assert result.stderr.splitlines()[-1] == "total=5"


def test_custom_pattern(logs, run):
    result = run("-d", logs["root"], "-a", 7, "-p", "*.gz")
    assert result.returncode == 0, result.stderr
    assert lines(result.stdout) == {f"deleted {logs['root'] / 'api.log.3.gz'}"}
    assert (logs["root"] / "worker" / "worker.log.1").exists()


def test_second_run_finds_nothing(logs, run):
    assert run("-d", logs["root"], "-a", 7).returncode == 0
    result = run("-d", logs["root"], "-a", 7)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr.splitlines()[-1] == "total=0"


def test_relative_dir(logs, tmp_path, run):
    rel = logs["root"].relative_to(tmp_path).as_posix()
    result = run("-d", rel, "-a", 7)
    assert result.returncode == 0, result.stderr
    assert lines(result.stdout) == {f"deleted {rel}/{p.relative_to(logs['root']).as_posix()}" for p in logs["old"]}


@pytest.mark.parametrize(
    "args",
    [(), ("-d", "{root}"), ("-a", "7"), ("-d", "{root}", "-a", "0"), ("-d", "{root}", "-a", "x"), ("-d", "{root}", "-a", "7", "-z"), ("-d", "{root}", "-a", "7", "extra")],
)
def test_usage_errors(logs, args, run):
    before = sorted(p.as_posix() for p in logs["root"].rglob("*"))
    result = run(*(a.format(root=logs["root"]) for a in args))
    assert result.returncode == 2
    assert result.stderr.startswith("Usage:")
    assert result.stdout == ""
    assert sorted(p.as_posix() for p in logs["root"].rglob("*")) == before


def test_missing_dir(tmp_path, run):
    result = run("-d", tmp_path / "khong-co", "-a", 7)
    assert result.returncode == 1
    assert result.stderr.strip()
    assert result.stdout == ""


@pytest.fixture
def fake_tools(tmp_path):
    """find và rm giả đứng đầu PATH để biết script có gọi chúng không; lớp an toàn là sandbox bwrap."""
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    for name in ("find", "rm"):
        tool = bindir / name
        tool.write_text(FAKE_TOOL)
        tool.chmod(0o755)
    log = tmp_path / "fake.log"
    return {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "FAKE_LOG": str(log)}, log


@pytest.mark.parametrize("target", ["/", "/tmp", "/var", "{tmp}/to-root", "{tmp}/to-root/usr/../home"])
def test_refuses_dangerous_dirs(tmp_path, fake_tools, target, run):
    (tmp_path / "to-root").symlink_to("/")
    env, log = fake_tools
    result = run("-d", target.format(tmp=tmp_path), "-a", 1, env_extra=env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr.strip()
    assert result.stdout == ""
    assert not log.exists(), f"Không được gọi find/rm với thư mục nguy hiểm: {log.read_text() if log.exists() else ''}"


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(ex.path("prune.sh"))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
