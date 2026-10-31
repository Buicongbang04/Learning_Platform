"""Chuyển bản release của Olist Shop bằng symlink `current`, có check sau khi chuyển và rollback."""

import argparse
import logging
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("release")
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def current_version(root: Path) -> str | None:
    # TODO 1: đọc symlink root/"current", trả tên release nó trỏ tới, không có thì None
    raise NotImplementedError


def switch(root: Path, version: str | None) -> None:
    # TODO 2: trỏ root/"current" tới "releases/<version>" (đường dẫn tương đối) một cách nguyên tử:
    #         tạo symlink tạm trong root rồi os.replace đè lên current; version None thì xoá current
    raise NotImplementedError


def run_check(command: str, cwd: Path, version: str, timeout: float) -> bool:
    # TODO 3: tách command bằng shlex.split, chạy bằng subprocess.run (không shell=True) trong cwd với
    #         RELEASE_VERSION=<version>, có timeout; trả False khi exit khác 0, quá giờ hoặc không có lệnh
    raise NotImplementedError


def deploy(args: argparse.Namespace) -> int:
    # TODO 4: version không khớp VERSION -> thoát 2; kiểm source; chép vào releases/<version> qua thư mục tạm rồi rename (đã có thì dùng lại);
    #         đang là bản hiện tại thì không làm gì; chuyển current; chạy check, hỏng thì chuyển lại bản cũ, trả 1;
    #         thành công thì thêm version vào .history; --dry-run chỉ log, không đổi gì
    raise NotImplementedError


def rollback(args: argparse.Namespace) -> int:
    # TODO 5: về bản đứng trước bản cuối trong .history, bỏ dòng cuối; không có bản trước thì trả 1
    raise NotImplementedError


def status(args: argparse.Namespace) -> int:
    version = current_version(args.root)
    if version is None:
        return 1
    print(version)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    dep = sub.add_parser("deploy")
    dep.add_argument("source", type=Path)
    dep.add_argument("--version", required=True)
    dep.add_argument("--check")
    dep.add_argument("--check-timeout", type=float, default=30.0)
    dep.add_argument("--dry-run", action="store_true")
    dep.set_defaults(func=deploy)
    rb = sub.add_parser("rollback")
    rb.add_argument("--dry-run", action="store_true")
    rb.set_defaults(func=rollback)
    st = sub.add_parser("status")
    st.set_defaults(func=status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
