import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Cần bash")
ORIGINAL = Path(__file__).parent / "fixtures" / "cleanup_releases.original.sh"
REVIEW_TEMPLATE = Path(__file__).parent / "fixtures" / "REVIEW.template.md"
UNSAFE_DELETE = re.compile(r"(?<![\w-])(?:/usr)?/bin/rm\b|\bcommand\s+rm\b|\\rm\b|-delete\b|\bunlink\b|\brmdir\b")
FAKE_RM = r'''#!{python}
import os, shutil, sys
sandbox = os.environ["SANDBOX"]
log = open(os.environ["RM_LOG"], "a")
log.write("CALL " + repr(sys.argv[1:]) + "\n")
args, paths, recursive, force = sys.argv[1:], [], False, False
while args:
    a = args.pop(0)
    if a == "--":
        paths += args
        break
    if a.startswith("--"):
        if a in ("--recursive",):
            recursive = True
        elif a in ("--force",):
            force = True
        elif a not in ("--verbose", "--one-file-system", "--preserve-root"):
            print(f"rm: unrecognized option '{a}'", file=sys.stderr)
            sys.exit(1)
    elif a.startswith("-") and len(a) > 1:
        for ch in a[1:]:
            if ch in "rR":
                recursive = True
            elif ch == "f":
                force = True
            elif ch not in "vdI":
                print(f"rm: invalid option -- '{ch}'", file=sys.stderr)
                sys.exit(1)
    else:
        paths.append(a)
rc = 0
for p in paths:
    name = os.path.basename(os.path.normpath(p))
    full = os.path.join(os.path.realpath(os.path.dirname(os.path.abspath(p))), name)
    if name in ("", ".", "..", "/") or not full.startswith(sandbox + os.sep):
        log.write("REFUSED " + p + "\n")
        print(f"rm: refusing to remove '{p}' (ngoài sandbox của test)", file=sys.stderr)
        rc = 1
        continue
    if os.path.islink(full) or os.path.isfile(full):
        os.unlink(full)
    elif os.path.isdir(full):
        if not recursive:
            print(f"rm: cannot remove '{p}': Is a directory", file=sys.stderr)
            rc = 1
            continue
        shutil.rmtree(full)
    elif not force:
        print(f"rm: cannot remove '{p}': No such file or directory", file=sys.stderr)
        rc = 1
sys.exit(rc)
'''


class Sandbox:
    def __init__(self, tmp_path: Path, script: Path):
        self.script = script
        self.root = tmp_path / "sandbox"
        self.workdir = self.root / "workdir"
        self.workdir.mkdir(parents=True)
        self.decoys = [self.workdir / n for n in ("r9", "keep-me.txt", "notes", "data.db")]
        for i, p in enumerate(self.decoys):
            p.write_text("decoy")
            os.utime(p, (time.time() - i * 3600,) * 2)
        self.bin = tmp_path / "fakebin"
        self.bin.mkdir()
        rm = self.bin / "rm"
        rm.write_text(FAKE_RM.replace("{python}", sys.executable))
        rm.chmod(0o755)
        self.log = tmp_path / "rm.log"

    def deploy_root(self, releases: list[str], current: str | None = None, tmp: list[str] | None = None, name: str = "olist-shop") -> Path:
        root = self.root / "srv" / name
        (root / "releases").mkdir(parents=True)
        now = time.time()
        for age, name in enumerate(releases):
            d = root / "releases" / name
            (d / "app").mkdir(parents=True)
            (d / "app" / "main.py").write_text(name)
            os.utime(d, (now - (age + 1) * 3600,) * 2)
        if current:
            (root / "current").symlink_to(Path("releases") / current)
        if tmp is not None:
            (root / "tmp").mkdir()
            for rel in tmp:
                f = root / "tmp" / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("cache")
        return root

    def run(self, *args):
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "SANDBOX": str(self.root.resolve()), "RM_LOG": str(self.log)}
        env.pop("CDPATH", None)
        return subprocess.run([BASH, str(self.script), *map(str, args)], capture_output=True, text=True, timeout=60, env=env, cwd=self.workdir)

    def refused(self) -> list[str]:
        return [line for line in self.log.read_text().splitlines() if line.startswith("REFUSED")] if self.log.exists() else []

    def rm_calls(self) -> int:
        return sum(1 for line in self.log.read_text().splitlines() if line.startswith("CALL")) if self.log.exists() else 0

    def decoys_intact(self) -> bool:
        return all(p.exists() for p in self.decoys)


def releases_left(root: Path) -> set[str]:
    return {p.name for p in (root / "releases").iterdir()}


def static_guard(script: Path) -> list[str]:
    if UNSAFE_DELETE.search(script.read_text(encoding="utf-8")):
        return ["Xoá bằng `rm` gọi qua PATH (không /bin/rm, command rm, \\rm, find -delete, unlink, rmdir)"]
    return []


def check_odd_names(script: Path, tmp_path: Path) -> list[str]:
    sb = Sandbox(tmp_path, script)
    root = sb.deploy_root(["r5", "r4", "r3", "r5 old", "-hotfix", "r1"], tmp=[])
    result = sb.run(root, 3)
    problems = []
    if result.returncode != 0:
        problems.append(f"exit {result.returncode}, cần 0: {result.stderr.strip()}")
    if releases_left(root) != {"r5", "r4", "r3"}:
        problems.append(f"Còn lại {sorted(releases_left(root))}, cần ['r3', 'r4', 'r5']")
    if set(result.stdout.splitlines()) != {"removed r5 old", "removed -hotfix", "removed r1"}:
        problems.append(f"stdout phải đúng các dòng 'removed <tên>': {result.stdout!r}")
    return problems + [f"rm bị gọi ngoài sandbox: {r}" for r in sb.refused()]


def check_root_with_space(script: Path, tmp_path: Path) -> list[str]:
    sb = Sandbox(tmp_path, script)
    root = sb.deploy_root(["r3", "r2", "r1"], tmp=["a.cache"], name="olist shop")
    result = sb.run(root, 2)
    problems = []
    if result.returncode != 0:
        problems.append(f"Đường dẫn có dấu cách: exit {result.returncode}, cần 0: {result.stderr.strip()}")
    if releases_left(root) != {"r3", "r2"}:
        problems.append(f"Đường dẫn có dấu cách: còn lại {sorted(releases_left(root))}, cần ['r2', 'r3']")
    if (root / "tmp" / "a.cache").exists():
        problems.append("Đường dẫn có dấu cách: tmp chưa được dọn")
    if not sb.decoys_intact():
        problems.append("Đường dẫn có dấu cách: đã xoá tệp trong cwd")
    return problems + [f"rm bị gọi ngoài sandbox: {r}" for r in sb.refused()]


def check_current_is_protected(script: Path, tmp_path: Path) -> list[str]:
    sb = Sandbox(tmp_path, script)
    root = sb.deploy_root(["r4", "r3", "r2", "r1"], current="r1", tmp=[])
    result = sb.run(root, 2)
    problems = []
    if result.returncode != 0:
        problems.append(f"exit {result.returncode}, cần 0")
    if releases_left(root) != {"r4", "r3", "r1"}:
        problems.append(f"Bản current (r1) phải được giữ dù cũ; còn lại {sorted(releases_left(root))}")
    if (root / "current").resolve() != (root / "releases" / "r1").resolve():
        problems.append("current phải còn trỏ tới r1")
    return problems


def check_missing_argument(script: Path, tmp_path: Path) -> list[str]:
    sb = Sandbox(tmp_path, script)
    result = sb.run()
    problems = []
    if result.returncode != 2 or not result.stderr.startswith("Usage:"):
        problems.append(f"Thiếu tham số: cần exit 2 và stderr bắt đầu bằng 'Usage:', được exit {result.returncode}")
    if not sb.decoys_intact():
        problems.append("Đã xoá tệp trong thư mục đang đứng (cwd) khi thiếu tham số")
    if sb.rm_calls():
        problems.append(f"Không được gọi rm khi thiếu tham số; refused: {sb.refused()}")
    return problems


def check_nonexistent_root(script: Path, tmp_path: Path) -> list[str]:
    sb = Sandbox(tmp_path, script)
    result = sb.run(sb.root / "khong-co")
    problems = []
    if result.returncode != 1 or not result.stderr.strip():
        problems.append(f"Thư mục không tồn tại: cần exit 1 kèm lỗi ở stderr, được exit {result.returncode}")
    if not sb.decoys_intact():
        problems.append("cd thất bại nhưng script vẫn chạy tiếp và xoá tệp trong cwd")
    if sb.rm_calls():
        problems.append("Không được gọi rm khi thư mục không tồn tại")
    return problems


def check_tmp_cleanup(script: Path, tmp_path: Path) -> list[str]:
    sb = Sandbox(tmp_path, script)
    root = sb.deploy_root(["r2", "r1"], tmp=["a.cache", ".hidden", "sub dir/x.cache"])
    result = sb.run(root, 3)
    problems = []
    if result.returncode != 0:
        problems.append(f"exit {result.returncode}, cần 0")
    if not (root / "tmp").is_dir():
        problems.append("Giữ lại thư mục tmp, chỉ xoá nội dung")
    elif list((root / "tmp").iterdir()):
        problems.append(f"tmp còn {sorted(p.name for p in (root / 'tmp').iterdir())}, phải xoá cả tệp ẩn")
    if releases_left(root) != {"r2", "r1"}:
        problems.append("Ít release hơn KEEP thì không xoá release nào")
    return problems + [f"rm bị gọi ngoài sandbox: {r}" for r in sb.refused()]


def check_bad_keep(script: Path, tmp_path: Path) -> list[str]:
    problems = []
    for i, keep in enumerate(("abc", "0", "-1", "2x")):
        sb = Sandbox(tmp_path / str(i), script)
        root = sb.deploy_root(["r3", "r2", "r1"], tmp=["a"])
        result = sb.run(root, keep)
        if result.returncode != 2 or not result.stderr.startswith("Usage:"):
            problems.append(f"KEEP={keep!r}: cần exit 2 và 'Usage:', được exit {result.returncode}")
        if releases_left(root) != {"r3", "r2", "r1"} or not (root / "tmp" / "a").exists():
            problems.append(f"KEEP={keep!r}: không được xoá gì")
    return problems


def check_no_tmp_dir(script: Path, tmp_path: Path) -> list[str]:
    sb = Sandbox(tmp_path, script)
    root = sb.deploy_root(["r2", "r1"])
    result = sb.run(root, 1)
    problems = []
    if result.returncode != 0:
        problems.append(f"Không có thư mục tmp vẫn phải chạy được, được exit {result.returncode}: {result.stderr.strip()}")
    if releases_left(root) != {"r2"}:
        problems.append(f"Còn lại {sorted(releases_left(root))}, cần ['r2']")
    return problems + [f"rm bị gọi ngoài sandbox: {r}" for r in sb.refused()]


def check_shellcheck(script: Path, tmp_path: Path) -> list[str]:
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(script)], capture_output=True, text=True)
    return [result.stdout] if result.returncode != 0 else []


CHECKS = {
    "odd_names": check_odd_names,
    "root_with_space": check_root_with_space,
    "current_is_protected": check_current_is_protected,
    "missing_argument": check_missing_argument,
    "nonexistent_root": check_nonexistent_root,
    "tmp_cleanup": check_tmp_cleanup,
    "bad_keep": check_bad_keep,
    "no_tmp_dir": check_no_tmp_dir,
    "shellcheck": check_shellcheck,
}
DEFECT_CHECKS = ["odd_names", "root_with_space", "current_is_protected", "missing_argument", "nonexistent_root", "tmp_cleanup", "bad_keep", "shellcheck"]


@pytest.mark.parametrize("name", list(CHECKS))
def test_refactored_script(name, tmp_path):
    script = ex.path("cleanup_releases.sh")
    problems = static_guard(script) or CHECKS[name](script, tmp_path)
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("name", DEFECT_CHECKS)
def test_check_catches_original_defect(name, tmp_path):
    assert CHECKS[name](ORIGINAL, tmp_path), f"Kiểm tra {name} phải bắt được lỗi của bản gốc"


def test_static_guard_catches_unsafe_delete(tmp_path):
    for line in ("/bin/rm -rf \"$d\"", "command rm -rf \"$d\"", "find \"$d\" -mtime +1 -delete", "\\rm -f x"):
        script = tmp_path / "s.sh"
        script.write_text(f"#!/usr/bin/env bash\n{line}\n")
        assert static_guard(script), line
    script.write_text('#!/usr/bin/env bash\nrm -rf -- "$d"\n')
    assert not static_guard(script)


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def review_problems(doc: str) -> list[str]:
    problems = []
    if "TODO" in doc:
        problems.append("Còn TODO")
    rows = [line.strip().strip("|").split("|") for line in section(doc, 1).splitlines() if line.strip().startswith("|")][2:]
    rows = [[c.strip() for c in r] for r in rows if len(r) >= 5 and all(c.strip() for c in r[:5])]
    if len(rows) < 6:
        problems.append(f"Bảng lỗi cần ít nhất 6 dòng đủ 5 cột, có {len(rows)}")
    if len(section(doc, 2).strip()) < 150:
        problems.append("Phần 2 (cách kiểm chứng) cần ít nhất 150 ký tự")
    if not re.search(r"^\s*-\s+\S", section(doc, 3), re.M):
        problems.append("Phần 3 cần ít nhất một gạch đầu dòng")
    return problems


def test_review_document():
    problems = review_problems(ex.read("REVIEW.md"))
    assert not problems, "\n".join(problems)


def test_review_check_catches_template():
    assert review_problems(REVIEW_TEMPLATE.read_text(encoding="utf-8"))
