import os
import subprocess

import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)


def sh(repo, cmd, *args, ok=True):
    return mlopskit.dvc_sh(repo, cmd, args, ok=ok)


@pytest.fixture()
def repo(tmp_path):
    ex.require_tool("dvc")
    ex.require_tool("git")
    r = tmp_path / "repo"
    r.mkdir()
    sh(r, "git init -q -b main . && dvc init -q && printf '/.site\\n/.gc\\n' >> .git/info/exclude && git add -A && git commit -q -m init")
    (r / "data").mkdir()
    for name in ("track.sh", "restore.sh"):
        (r / name).write_text(ex.read(name))
    sh(r, "git add track.sh restore.sh && git commit -q -m scripts")
    return r


def write_csv(repo, rows):
    (repo / "data" / "trips.csv").write_text("trip_id,distance\n" + "".join(f"{i},{d}\n" for i, d in rows))


def pointer_md5(repo):
    text = (repo / "data" / "trips.csv.dvc").read_text()
    return next(line.split(":")[1].strip() for line in text.splitlines() if "md5:" in line)


def test_track_puts_pointer_in_git_and_data_in_cache(repo):
    write_csv(repo, [(1, 1.2), (2, 3.4)])
    sh(repo, "bash track.sh data/trips.csv")
    tracked = sh(repo, "git ls-files").stdout.split()
    assert "data/trips.csv.dvc" in tracked
    assert "data/trips.csv" not in tracked
    assert "trips.csv" in (repo / "data" / ".gitignore").read_text()
    md5 = pointer_md5(repo)
    assert (repo / ".dvc" / "cache" / "files" / "md5" / md5[:2] / md5[2:]).is_file()
    assert sh(repo, "git status --porcelain").stdout.strip() == ""
    assert "track data/trips.csv" in sh(repo, "git log -1 --format=%s").stdout


def test_new_data_version_is_new_commit(repo):
    write_csv(repo, [(1, 1.2)])
    sh(repo, "bash track.sh data/trips.csv")
    first = pointer_md5(repo)
    write_csv(repo, [(1, 1.2), (2, 5.5)])
    sh(repo, "bash track.sh data/trips.csv")
    assert pointer_md5(repo) != first
    log = sh(repo, "git log --format=%s").stdout.splitlines()
    assert log.count("track data/trips.csv") == 2


def test_restore_old_version_from_commit(repo):
    write_csv(repo, [(1, 1.2)])
    sh(repo, "bash track.sh data/trips.csv")
    v1 = (repo / "data" / "trips.csv").read_text()
    commit1 = sh(repo, "git rev-parse HEAD").stdout.strip()
    write_csv(repo, [(1, 1.2), (2, 5.5)])
    sh(repo, "bash track.sh data/trips.csv")
    head = sh(repo, "git rev-parse HEAD").stdout.strip()
    sh(repo, f"bash restore.sh {commit1} data/trips.csv")
    assert (repo / "data" / "trips.csv").read_text() == v1
    assert sh(repo, "git rev-parse HEAD").stdout.strip() == head
    sh(repo, "bash restore.sh HEAD data/trips.csv")
    assert (repo / "data" / "trips.csv").read_text().count("\n") == 3
