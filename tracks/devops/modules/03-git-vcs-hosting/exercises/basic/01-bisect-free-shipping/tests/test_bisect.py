import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from testkit import Exercise, GitRepo, git_env, run_sandboxed


def load_builder():
    spec = importlib.util.spec_from_file_location("bisect_shop_repo", Path(__file__).parent / "fixtures" / "build_shop_repo.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shop = load_builder()

ex = Exercise(__file__)
NAIVE = Path(__file__).parent / "fixtures" / "naive_check.sh"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None or shutil.which("git") is None, reason="Cần bash và git")


@pytest.fixture
def home(tmp_path):
    path = tmp_path / "home"
    path.mkdir()
    return path


def build(tmp_path, home, layout):
    repo = tmp_path / "olist-shop"
    return repo, shop.build(repo, layout, home)


def sandboxed(cmd, tmp_path, repo, home, timeout=60):
    return run_sandboxed([str(c) for c in cmd], writable=[tmp_path], cwd=repo, env=git_env(home), timeout=timeout)


def tgit(tmp_path, repo, home, *args):
    """git sau khi script của người học đã chạy trong repo: cấu hình repo có thể đã bị sửa, nên cũng chạy trong sandbox."""
    tainted = GitRepo(repo, home, writable=[tmp_path])
    tainted.taint()
    return tainted.out(*args, timeout=60)


def check_at(tmp_path, repo, home, sha, script):
    shop.git(repo, home, "checkout", "-q", sha)
    try:
        return sandboxed([BASH, script], tmp_path, repo, home)
    finally:
        tgit(tmp_path, repo, home, "checkout", "-q", "main")


@pytest.mark.parametrize(
    ("index", "expected", "why"),
    [
        (0, 0, "commit đầu, miễn phí ship đúng"),
        (23, 0, "ngay trước đoạn hỏng"),
        (24, 125, "shipping.py lỗi cú pháp, không kiểm được"),
        (25, 125, "shipping.py lỗi cú pháp, không kiểm được"),
        (28, 125, "thiếu rates.json, import lỗi"),
        (30, 0, "ngay trước commit gây lỗi"),
        (31, 1, "commit gây lỗi"),
        (47, 1, "HEAD vẫn lỗi"),
    ],
    ids=["commit-0", "commit-23", "commit-24", "commit-25", "commit-28", "commit-30", "commit-31", "commit-47"],
)
def test_check_script_exit_codes(tmp_path, home, index, expected, why):
    repo, info = build(tmp_path, home, "A")
    result = check_at(tmp_path, repo, home, info["shas"][index], ex.path("check_free_shipping.sh"))
    assert result.returncode == expected, f"commit #{index} ({why}): cần exit {expected}, nhận {result.returncode}\n{result.stderr}"


def test_check_script_leaves_tree_clean(tmp_path, home):
    repo, info = build(tmp_path, home, "A")
    check_at(tmp_path, repo, home, info["shas"][31], ex.path("check_free_shipping.sh"))
    status = tgit(tmp_path, repo, home, "status", "--porcelain", "--ignored")
    assert status == "", f"Script kiểm không được để lại tệp trong repo (bisect checkout sẽ hỏng):\n{status}"


@pytest.mark.parametrize("layout", ["A", "B"])
def test_find_first_bad(tmp_path, home, layout):
    repo, info = build(tmp_path, home, layout)
    result = sandboxed([BASH, ex.path("find_first_bad.sh"), "v1.0.0", "main"], tmp_path, repo, home, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    expected = info["shas"][info["layout"].bad]
    lines = result.stdout.strip().splitlines()
    assert lines and lines[-1] == f"first-bad {expected}", f"Dòng cuối stdout phải là 'first-bad {expected}', nhận {lines[-1:] or 'rỗng'}"


@pytest.mark.parametrize("layout", ["A", "B"])
def test_find_first_bad_cleans_up(tmp_path, home, layout):
    repo, _ = build(tmp_path, home, layout)
    sandboxed([BASH, ex.path("find_first_bad.sh"), "v1.0.0", "main"], tmp_path, repo, home, timeout=120)
    assert tgit(tmp_path, repo, home, "symbolic-ref", "--short", "HEAD") == "main"
    assert not (repo / ".git" / "BISECT_LOG").exists(), "Chưa chạy git bisect reset"
    assert not (repo / ".git" / "BISECT_START").exists(), "Chưa chạy git bisect reset"
    assert tgit(tmp_path, repo, home, "status", "--porcelain") == ""


def test_find_first_bad_reports_failure(tmp_path, home):
    repo, info = build(tmp_path, home, "A")
    result = sandboxed([BASH, ex.path("find_first_bad.sh"), "main", "v1.0.0"], tmp_path, repo, home, timeout=120)
    assert result.returncode == 1, f"good và bad đảo ngược thì bisect không kết luận được: cần exit 1\n{result.stdout}{result.stderr}"
    assert not re.search(r"^first-bad ", result.stdout, re.M)
    assert tgit(tmp_path, repo, home, "symbolic-ref", "--short", "HEAD") == "main"
    assert not (repo / ".git" / "BISECT_START").exists(), "Lỗi cũng phải git bisect reset"


@pytest.fixture(autouse=True)
def git_version():
    ex.require_tool("git", min_version="2.30")


def test_learner_git_config_never_runs_outside_sandbox(tmp_path, tmp_path_factory, home):
    """Script của người học có thể đặt core.hooksPath hay core.fsmonitor; lệnh git của test không được chạy chúng ngoài sandbox."""
    repo, info = build(tmp_path, home, "A")
    outside = tmp_path_factory.mktemp("outside-sandbox")
    marker = outside / "pwned"
    hooks = tmp_path / "evil-hooks"
    hooks.mkdir()
    for name in ("post-checkout", "fsmonitor"):
        hook = hooks / name
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 0\n")
        hook.chmod(0o755)
    setup = sandboxed(
        ["sh", "-c", f"git config core.hooksPath '{hooks}' && git config core.fsmonitor '{hooks / 'fsmonitor'}'"], tmp_path, repo, home
    )
    assert setup.returncode == 0, setup.stderr
    check_at(tmp_path, repo, home, info["shas"][3], NAIVE)
    tgit(tmp_path, repo, home, "status", "--porcelain")
    shop.git(repo, home, "checkout", "-q", info["shas"][5])
    shop.git(repo, home, "status", "--porcelain")
    assert not marker.exists(), "Hook do người học cấu hình đã chạy ngoài sandbox"
    subprocess.run(["git", "checkout", "-q", "main"], cwd=repo, env=git_env(home), capture_output=True)
    assert marker.exists(), "Kiểm tra vô nghĩa: hook giả không chạy cả khi gọi git không bảo vệ"


def test_builder_is_deterministic(tmp_path):
    first = shop.build(tmp_path / "one", "A", tmp_path / "h1")["shas"]
    second = shop.build(tmp_path / "two", "A", tmp_path / "h2")["shas"]
    assert first == second


def test_naive_check_is_caught(tmp_path, home):
    """Script ngây thơ coi lỗi import là 'bad': bài phải bắt được, và bisect với nó ra sai commit."""
    repo, info = build(tmp_path, home, "A")
    assert check_at(tmp_path, repo, home, info["shas"][24], NAIVE).returncode == 1
    sandboxed(["git", "bisect", "start", "main", "v1.0.0"], tmp_path, repo, home)
    sandboxed(["git", "bisect", "run", BASH, NAIVE], tmp_path, repo, home, timeout=120)
    found = tgit(tmp_path, repo, home, "rev-parse", "refs/bisect/bad")
    assert found != info["shas"][info["layout"].bad]
    assert found in {info["shas"][i] for i in [*info["layout"].syntax, *info["layout"].missing_rates]}


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    for name in ("check_free_shipping.sh", "find_first_bad.sh"):
        result = subprocess.run(["shellcheck", "-S", "style", str(ex.path(name))], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout
