import re
import shutil
import subprocess
from pathlib import Path

import pytest

from capstonekit import make, output
from testkit import ROOT, use_solution

ROOT_FILES = ("README.md", "LICENSE", ".gitignore", "Makefile")
TARGETS = ("survey", "bundle", "install", "verify")
SECRET_NAMES = re.compile(r"(^|/)(id_[^/]*|[^/]*\.pem|[^/]*\.key|\.env|\.env\.(?!example$)[^/]+)$")
MUST_IGNORE = ("lab.pem", "keys/id_ed25519", "tls/server.key", ".env", "delivery/.env", "quillo-1.0.0.tar",
               "dist/bundle/quillo-1.0.0.tar", "data/cuad/contract.pdf")
IMPORTS = re.compile(r"^\s*(?:import|from)\s+(?:testkit|fdekit)\b|-m\s+(?:testkit|fdekit)\b|\b(?:testkit|fdekit)\.py\b",
                     re.M)
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
REAL_SECRET = re.compile(r"\b(QUILLO_ADMIN_TOKEN|QUILLO_DB_PASSWORD)\s*[=:]\s*['\"]?[A-Za-z0-9+/_-]{16,}")
FENCE = re.compile(r"^(```|~~~)")
LEARNING_REPO_PATH = re.compile(r"/DataScience[^/\s]*/(?:tracks|testkit|fdekit|setup)\b")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30,
                          stdin=subprocess.DEVNULL)


@pytest.fixture
def repo(capstone, tmp_path) -> Path:
    """Repo git cần chấm. SOLUTION=1: bản sao của lời giải tham chiếu, `git init` + `git add -A` trong tmp_path."""
    if use_solution():
        copy = tmp_path / "project"
        shutil.copytree(capstone, copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        assert git(copy, "init", "-q").returncode == 0
        added = git(copy, "add", "-A")
        assert added.returncode == 0, added.stderr
        return copy
    top = git(capstone, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        pytest.fail(f"{capstone} chưa phải repo git: chạy `git init` trong đó")
    if Path(top.stdout.strip()).resolve() != capstone:
        pytest.fail(f"FDE_CAPSTONE_DIR={capstone} phải là gốc của một repo git riêng, không phải thư mục con của "
                    f"{top.stdout.strip()}")
    return capstone


def tracked(repo: Path) -> list[str]:
    result = git(repo, "ls-files", "-z")
    assert result.returncode == 0, result.stderr
    files = [name for name in result.stdout.split("\0") if name]
    if not files:
        pytest.fail("Repo chưa có tệp nào được `git add`/commit")
    return files


def h2_count(text: str) -> int:
    count, fenced = 0, False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            count += 1
    return count


def test_m00_layout(repo):
    files = set(tracked(repo))
    missing = [name for name in ROOT_FILES if name not in files]
    assert not missing, f"Chưa có (hoặc chưa git add) ở gốc repo: {missing}"
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert h2_count(readme) >= 4, (
        "README.md cần ít nhất 4 phần '## ' (khách hàng, ràng buộc, kiến trúc, cách chạy...)")
    assert (repo / "LICENSE").read_text(encoding="utf-8").strip(), "LICENSE đang rỗng"
    visible = [repo] if repo.is_relative_to("/tmp") else []
    result = make(repo, "-n", *TARGETS, writable=visible)
    assert result.returncode == 0, f"`make -n {' '.join(TARGETS)}` thoát mã {result.returncode}\n{output(result)}"


def test_m00_standalone(repo):
    problems = []
    for name in tracked(repo):
        path = repo / name
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="replace")
        if IMPORTS.search(text):
            problems.append(f"{name}: import/gọi testkit hoặc fdekit")
        found = LEARNING_REPO_PATH.search(text)
        if str(ROOT) in text or found:
            problems.append(f"{name}: chứa đường dẫn vào repo học ({found.group(0) if found else ROOT})")
    assert not problems, "Repo capstone phải tự chứa:\n" + "\n".join(problems)


def test_m00_no_secrets_committed(repo):
    files = tracked(repo)
    leaked = [name for name in files if SECRET_NAMES.search(name)]
    assert not leaked, f"Tệp không được commit (khoá, .env): {leaked}"
    for name in files:
        path = repo / name
        if not path.is_file() or path.is_symlink():
            continue
        text = path.read_bytes().decode("utf-8", errors="replace")
        assert not PRIVATE_KEY.search(text), f"{name} chứa private key"
        assert not REAL_SECRET.search(text), f"{name} chứa giá trị token/mật khẩu quillo thật"
    unignored = [p for p in MUST_IGNORE if git(repo, "check-ignore", "-q", "--no-index", p).returncode != 0]
    assert not unignored, f".gitignore chưa chặn: {unignored}"
