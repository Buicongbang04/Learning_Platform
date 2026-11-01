import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from testkit import Exercise, GitRepo, git_env, run_sandboxed

ex = Exercise(__file__)
NAIVE = Path(__file__).parent / "fixtures" / "naive_rescue.sh"
BASH = shutil.which("bash")
BRANCH = "feature/pix-payment"
pytestmark = pytest.mark.skipif(BASH is None or shutil.which("git") is None, reason="Cần bash và git")


@pytest.fixture(autouse=True)
def git_version():
    ex.require_tool("git", min_version="2.30")



class Repo:
    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.path = tmp_path / "olist-shop"
        self.path.mkdir()
        self.repo = GitRepo(self.path, self.home, writable=[tmp_path])
        self.git("init", "-q")

    def git(self, *args: str, check: bool = True) -> str:
        return self.repo.out(*args, check=check)

    def commit(self, name: str, message: str) -> str:
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a") as handle:
            handle.write(f"{message} {uuid.uuid4()}\n")
        self.git("add", name)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def ref(self, name: str) -> str | None:
        out = self.git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}", check=False)
        return out or None

    def run(self, script: Path, *args: str):
        self.repo.taint()
        return run_sandboxed([BASH, script, *args], writable=[self.tmp], cwd=self.path, env=git_env(self.home), timeout=30)

    def state(self) -> tuple:
        return (
            self.git("symbolic-ref", "HEAD"),
            self.git("rev-parse", "main"),
            self.git("status", "--porcelain", "--untracked-files=all"),
            self.git("diff"),
            self.git("diff", "--cached"),
        )


def incident(tmp_path: Path) -> tuple[Repo, dict[str, str]]:
    """Lịch sử giống sự cố: reset --hard nhầm trên main, rồi xoá nhánh feature chưa merge."""
    repo = Repo(tmp_path)
    for i in range(1, 6):
        repo.commit("api/orders.py", f"feat(orders): step {i}")
    repo.git("switch", "-q", "-c", BRANCH)
    repo.commit("api/payments/pix.py", "feat(payments): pix qr code")
    repo.git("switch", "-q", "main")
    repo.commit("api/orders.py", "feat(orders): cancel endpoint")
    repo.git("switch", "-q", BRANCH)
    pix_tip = repo.commit("api/payments/pix.py", "feat(payments): pix webhook")
    repo.git("switch", "-q", "main")
    repo.commit("api/orders.py", "fix(orders): status on cancel")
    oops = repo.commit("api/debug.py", "debug: print every order")
    repo.git("reset", "-q", "--hard", "HEAD~1")
    lost_tip = repo.commit("api/orders.py", "feat(orders): refund endpoint")
    repo.git("switch", "-q", "-c", "docs/runbook")
    repo.commit("docs/runbook.md", "docs: refund runbook")
    repo.git("switch", "-q", "main")
    repo.git("reset", "-q", "--hard", "HEAD~3")
    after = repo.commit("api/hotfix.py", "fix: hotfix after reset")
    repo.git("branch", "-q", "-D", BRANCH)
    (repo.path / "api" / "orders.py").write_text("đang sửa dở, chưa commit\n")
    (repo.path / "NOTES.txt").write_text("tệp chưa track\n")
    return repo, {"lost_tip": lost_tip, "pix_tip": pix_tip, "oops": oops, "after": after}


def test_rescues_lost_main_and_deleted_branch(tmp_path):
    repo, shas = incident(tmp_path)
    result = repo.run(ex.path("rescue.sh"), BRANCH)
    assert result.returncode == 0, result.stdout + result.stderr
    assert repo.ref("rescue/main") == shas["lost_tip"], "rescue/main phải trỏ vào tip của main ngay trước lần reset gần nhất"
    assert repo.ref(BRANCH) == shas["pix_tip"], f"{BRANCH} phải trỏ vào commit cuối của nhánh trước khi bị xoá"
    assert result.stdout.splitlines() == [f"rescue/main {shas['lost_tip']}", f"{BRANCH} {shas['pix_tip']}"]


def test_does_not_touch_main_head_or_worktree(tmp_path):
    repo, shas = incident(tmp_path)
    before = repo.state()
    result = repo.run(ex.path("rescue.sh"), BRANCH)
    assert result.returncode == 0, result.stdout + result.stderr
    assert repo.state() == before, "Không được đổi main, HEAD, index hay working tree (không checkout, không reset)"
    assert repo.git("rev-parse", "main") == shas["after"]


def test_second_run_is_idempotent(tmp_path):
    repo, shas = incident(tmp_path)
    first = repo.run(ex.path("rescue.sh"), BRANCH)
    second = repo.run(ex.path("rescue.sh"), BRANCH)
    assert first.returncode == 0 and second.returncode == 0, second.stderr
    assert second.stdout == first.stdout
    assert repo.ref("rescue/main") == shas["lost_tip"]


def test_refuses_to_overwrite_existing_branch(tmp_path):
    repo, shas = incident(tmp_path)
    first_commit = repo.git("rev-list", "--max-parents=0", "main")
    repo.git("branch", "rescue/main", first_commit)
    result = repo.run(ex.path("rescue.sh"), BRANCH)
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr.strip()
    assert repo.ref("rescue/main") == first_commit
    assert repo.ref(BRANCH) is None, "Lỗi thì không tạo nhánh nào"


def test_no_reset_in_history(tmp_path):
    repo = Repo(tmp_path)
    repo.commit("api/orders.py", "feat: one")
    repo.git("switch", "-q", "-c", BRANCH)
    repo.commit("api/payments/pix.py", "feat: pix")
    repo.git("switch", "-q", "main")
    repo.git("branch", "-q", "-D", BRANCH)
    result = repo.run(ex.path("rescue.sh"), BRANCH)
    assert result.returncode == 1, result.stdout + result.stderr
    assert repo.ref("rescue/main") is None and repo.ref(BRANCH) is None


def test_unknown_branch(tmp_path):
    repo, _ = incident(tmp_path)
    result = repo.run(ex.path("rescue.sh"), "feature/khong-ton-tai")
    assert result.returncode == 1, result.stdout + result.stderr
    assert repo.ref("rescue/main") is None


def test_usage(tmp_path):
    repo, _ = incident(tmp_path)
    result = repo.run(ex.path("rescue.sh"))
    assert result.returncode == 2
    assert result.stderr.startswith("Usage:")


def test_naive_rescue_is_caught(tmp_path):
    """`main@{1}` và `@{-1}` đúng ngay sau sự cố, sai khi đã có thêm commit và checkout: bài phải bắt được."""
    repo, shas = incident(tmp_path)
    result = repo.run(NAIVE, BRANCH)
    assert result.returncode == 0, result.stderr
    assert repo.ref("rescue/main") != shas["lost_tip"]
    assert repo.ref(BRANCH) != shas["pix_tip"]


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(ex.path("rescue.sh"))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
