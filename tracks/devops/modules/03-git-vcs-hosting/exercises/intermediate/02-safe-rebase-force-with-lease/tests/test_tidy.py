import os
import shutil
import subprocess
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
NAIVE = Path(__file__).parent / "fixtures" / "naive_tidy.sh"
BASH = shutil.which("bash")
BRANCH = "feature/pix-payment"
pytestmark = pytest.mark.skipif(BASH is None or shutil.which("git") is None, reason="Cần bash và git")

BASE_PIX = "def pay(order):\n    return 'todo'\n"
QR_TYPO = "def pay(order):\n    return qr_cdoe(order)\n"
QR = "def pay(order):\n    return qr_code(order)\n"
WEBHOOK = QR + "\n\ndef webhook(event):\n    return event['status']\n"
WEBHOOK_FIXED = QR + "\n\ndef webhook(event):\n    if 'status' not in event:\n        raise ValueError('missing status')\n    return event['status']\n"
SUBJECTS = ["feat(payments): pix qr code", "feat(payments): pix webhook"]


def git_env(home: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Minh Tran",
        "GIT_AUTHOR_EMAIL": "minh@olist-shop.example",
        "GIT_COMMITTER_NAME": "Minh Tran",
        "GIT_COMMITTER_EMAIL": "minh@olist-shop.example",
        "GIT_AUTHOR_DATE": "2026-06-01T10:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-06-01T10:00:00+00:00",
        "GIT_EDITOR": "true",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


class Clone:
    def __init__(self, path: Path, home: Path):
        self.path = path
        self.home = home

    def git(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", *args],
            cwd=self.path, env=git_env(self.home), capture_output=True, text=True, check=check,
        )
        return result.stdout.strip()

    def commit(self, name: str, content: str, message: str) -> str:
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self.git("add", name)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")


class World:
    """origin.git (bare) + seed (đồng nghiệp, CI) + work (repo của người học, đang ở nhánh feature)."""

    def __init__(self, tmp_path: Path, push_feature: bool = True):
        self.tmp = tmp_path
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.origin = tmp_path / "origin.git"
        subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "init", "-q", "--bare", str(self.origin)],
            env=git_env(self.home), check=True, capture_output=True,
        )
        self.seed = self.clone("seed")
        self.seed.commit("README.md", "# Olist Shop\n", "chore: init")
        self.seed.commit("payments/pix.py", BASE_PIX, "feat(payments): pix stub")
        self.seed.git("push", "-q", "origin", "main")
        self.work = self.clone("work")
        self.work.git("switch", "-q", "-c", BRANCH)
        self.work.commit("payments/pix.py", QR_TYPO, SUBJECTS[0])
        self.work.commit("payments/pix.py", QR, f"fixup! {SUBJECTS[0]}")
        self.work.commit("payments/pix.py", WEBHOOK, SUBJECTS[1])
        self.work.commit("payments/pix.py", WEBHOOK_FIXED, f"fixup! {SUBJECTS[1]}")
        if push_feature:
            self.work.git("push", "-q", "-u", "origin", BRANCH)

    def clone(self, name: str) -> Clone:
        path = self.tmp / name
        subprocess.run(["git", "clone", "-q", str(self.origin), str(path)], env=git_env(self.home), check=True, capture_output=True)
        return Clone(path, self.home)

    def advance_main(self, name: str = "api/orders.py", content: str = "def orders():\n    return []\n") -> str:
        self.seed.git("pull", "-q", "--ff-only", "origin", "main")
        sha = self.seed.commit(name, content, "feat(orders): list endpoint")
        self.seed.git("push", "-q", "origin", "main")
        return sha

    def teammate_pushes(self) -> str:
        self.seed.git("fetch", "-q", "origin")
        self.seed.git("switch", "-q", "-c", BRANCH, f"origin/{BRANCH}")
        sha = self.seed.commit("payments/refund.py", "def refund():\n    return True\n", "feat(payments): pix refund")
        self.seed.git("push", "-q", "origin", BRANCH)
        return sha

    def remote(self, ref: str) -> str:
        return self.work.git("ls-remote", str(self.origin), f"refs/heads/{ref}").split("\t")[0]

    def run(self, script: Path, *args: str):
        return run_sandboxed([BASH, script, *args], writable=[self.tmp], cwd=self.work.path, env=git_env(self.home), timeout=60)


def subjects(clone: Clone, base: str) -> list[str]:
    return clone.git("log", "--reverse", "--format=%s", f"{base}..HEAD").splitlines()


def test_squashes_fixups_rebases_and_pushes(tmp_path):
    world = World(tmp_path)
    main_tip = world.advance_main()
    result = world.run(ex.path("tidy_branch.sh"))
    assert result.returncode == 0, result.stdout + result.stderr
    head = world.work.git("rev-parse", "HEAD")
    assert world.work.git("symbolic-ref", "--short", "HEAD") == BRANCH
    assert world.work.git("merge-base", "HEAD", main_tip) == main_tip, "Nhánh phải nằm trên tip mới nhất của origin/main"
    assert subjects(world.work, main_tip) == SUBJECTS, "Mỗi fixup! phải gộp vào commit gốc của nó, giữ thứ tự"
    assert world.work.git("show", "HEAD:payments/pix.py") + "\n" == WEBHOOK_FIXED
    assert world.work.git("show", "HEAD:api/orders.py")
    assert world.remote(BRANCH) == head, "Nhánh trên remote phải là kết quả đã rebase"
    assert world.remote("main") == main_tip
    assert result.stdout.strip().splitlines()[-1] == f"pushed {BRANCH} {head}"


def test_does_not_clobber_teammate_push(tmp_path):
    world = World(tmp_path)
    world.advance_main()
    teammate = world.teammate_pushes()
    result = world.run(ex.path("tidy_branch.sh"))
    assert result.returncode == 1, f"Remote đã có commit của đồng nghiệp: cần exit 1\n{result.stdout}{result.stderr}"
    assert world.remote(BRANCH) == teammate, "Commit của đồng nghiệp trên remote đã bị ghi đè"


def test_conflict_aborts_cleanly(tmp_path):
    world = World(tmp_path)
    before = world.work.git("rev-parse", "HEAD")
    remote_before = world.remote(BRANCH)
    world.advance_main("payments/pix.py", "def pay(order):\n    return 'pending'\n")
    result = world.run(ex.path("tidy_branch.sh"))
    assert result.returncode == 1, result.stdout + result.stderr
    assert world.work.git("symbolic-ref", "--short", "HEAD") == BRANCH, "Phải git rebase --abort, không để repo ở giữa rebase"
    assert world.work.git("rev-parse", "HEAD") == before
    assert not (world.work.path / ".git" / "rebase-merge").exists()
    assert world.work.git("status", "--porcelain") == ""
    assert world.remote(BRANCH) == remote_before


def test_pushes_new_branch(tmp_path):
    world = World(tmp_path, push_feature=False)
    main_tip = world.advance_main()
    result = world.run(ex.path("tidy_branch.sh"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert subjects(world.work, main_tip) == SUBJECTS
    assert world.remote(BRANCH) == world.work.git("rev-parse", "HEAD")


def test_refuses_main(tmp_path):
    world = World(tmp_path)
    world.work.git("switch", "-q", "main")
    world.work.commit("api/x.py", "x = 1\n", "chore: local")
    local = world.work.git("rev-parse", "HEAD")
    remote_main = world.remote("main")
    result = world.run(ex.path("tidy_branch.sh"))
    assert result.returncode == 2, result.stdout + result.stderr
    assert world.remote("main") == remote_main
    assert world.work.git("rev-parse", "HEAD") == local


def test_refuses_detached_head(tmp_path):
    world = World(tmp_path)
    world.work.git("switch", "-q", "--detach", "HEAD~1")
    result = world.run(ex.path("tidy_branch.sh"))
    assert result.returncode == 2, result.stdout + result.stderr


def test_refuses_dirty_tree(tmp_path):
    world = World(tmp_path)
    world.advance_main()
    before = world.work.git("rev-parse", "HEAD")
    remote_before = world.remote(BRANCH)
    (world.work.path / "payments" / "pix.py").write_text("đang sửa dở\n")
    result = world.run(ex.path("tidy_branch.sh"))
    assert result.returncode == 2, result.stdout + result.stderr
    assert world.work.git("rev-parse", "HEAD") == before
    assert (world.work.path / "payments" / "pix.py").read_text() == "đang sửa dở\n"
    assert world.remote(BRANCH) == remote_before


def test_naive_lease_is_caught(tmp_path):
    """fetch toàn bộ rồi --force-with-lease không kèm giá trị: lease so với ref vừa fetch, nên vẫn ghi đè đồng nghiệp."""
    world = World(tmp_path)
    world.advance_main()
    teammate = world.teammate_pushes()
    result = world.run(NAIVE)
    assert result.returncode == 0, result.stderr
    assert world.remote(BRANCH) != teammate


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(ex.path("tidy_branch.sh"))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
