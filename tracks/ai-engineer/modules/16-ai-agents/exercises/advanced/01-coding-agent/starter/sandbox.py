"""Sandbox chạy test cho coding agent: đường dẫn an toàn, pytest trong tiến trình con có timeout, chấm bằng test ẩn."""

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestRun:
    passed: int
    failed: int
    errors: int
    timed_out: bool
    returncode: int | None
    output: str
    network_isolated: bool = False

    @property
    def ok(self) -> bool:
        return self.passed > 0 and self.failed == 0 and self.errors == 0 and not self.timed_out


_UNSHARE: bool | None = None


def network_isolation_available() -> bool:
    """`unshare -rn` (user + network namespace, không cần root) chạy được trên máy này không. Kết quả được nhớ lại."""
    global _UNSHARE
    if _UNSHARE is None:
        exe = shutil.which("unshare")
        _UNSHARE = bool(exe) and subprocess.run([exe, "-rn", "true"], capture_output=True).returncode == 0
    return _UNSHARE


def safe_path(root: Path, rel: str) -> Path:
    """Đường dẫn tuyệt đối (đã resolve) của `rel` bên trong `root`.

    `rel` rỗng, tuyệt đối, hoặc trỏ ra ngoài `root` sau khi resolve (`../`, symlink ra ngoài) -> ValueError.
    """
    # TODO
    raise NotImplementedError


def run_pytest(workdir: Path, timeout: float = 20, isolate_network: bool = True,
               args: list[str] | None = None) -> TestRun:
    """Chạy `python -m pytest -q -p no:cacheprovider --no-header *args` trong `workdir`, ở tiến trình con.

    - Dùng sys.executable (cùng môi trường), cwd=workdir, môi trường tối thiểu (PATH, HOME=workdir, PYTHONPATH=workdir,
      PYTHONDONTWRITEBYTECODE=1, LANG=C.UTF-8): không truyền biến môi trường của bạn (key API, token) vào sandbox.
    - isolate_network và network_isolation_available(): chạy dưới `unshare -rn` (không có mạng); ghi network_isolated.
    - Tiến trình con chạy trong session riêng; quá `timeout` giây thì giết CẢ NHÓM tiến trình, trả timed_out=True,
      passed = failed = errors = 0, returncode None.
    - passed/failed/errors đọc từ dòng tóm tắt cuối của pytest ("3 passed, 1 failed", "1 error"...).
    - output: 4 000 ký tự cuối của stdout+stderr.
    """
    # TODO
    raise NotImplementedError


HOOK_FILES = {"conftest.py", "sitecustomize.py", "usercustomize.py"}


def source_files(workdir: Path) -> dict[str, str]:
    """{đường dẫn tương đối dạng posix: nội dung} của mọi tệp .py trong workdir, TRỪ thư mục tests/ và các tệp mà pytest
    hay Python tự nạp khi khởi động (HOOK_FILES): agent ghi một conftest.py hay sitecustomize.py là sửa được kết quả của
    test ẩn mà không cần đụng vào thư mục tests/."""
    return {p.relative_to(workdir).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(Path(workdir).rglob("*.py"))
            if "tests" not in p.relative_to(workdir).parts and p.name not in HOOK_FILES}


def grade(task_dir: Path, workdir: Path, timeout: float = 20) -> TestRun:
    """Chấm kết quả của agent bằng test ẩn.

    Chỉ chép những tệp có đường dẫn nằm trong source_files(task_dir / "repo") (danh sách tệp mã nguồn GỐC của task),
    lấy nội dung từ workdir (tệp agent đã xoá thì bỏ qua), vào một thư mục tạm mới; đặt task_dir/hidden/test_hidden.py
    vào tests/ của thư mục đó, rồi run_pytest. Mọi tệp agent tự thêm (một `pytest.py` giả che pytest thật qua
    PYTHONPATH, `conftest.py`, `sitecustomize.py`...) và thư mục tests/ của agent đều không được chép.
    """
    # TODO
    raise NotImplementedError
