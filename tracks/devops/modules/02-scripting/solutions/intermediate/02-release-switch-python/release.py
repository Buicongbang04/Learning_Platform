"""Chuyển bản release của Olist Shop bằng symlink `current`, có check sau khi chuyển và rollback."""

import argparse
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("release")
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def current_version(root: Path) -> str | None:
    link = root / "current"
    if not link.is_symlink():
        return None
    return Path(os.readlink(link)).name


def switch(root: Path, version: str | None) -> None:
    link = root / "current"
    if version is None:
        link.unlink(missing_ok=True)
        return
    tmp = root / f".current.{os.getpid()}"
    tmp.unlink(missing_ok=True)
    tmp.symlink_to(Path("releases") / version)
    os.replace(tmp, link)


def run_check(command: str, cwd: Path, version: str, timeout: float) -> bool:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        log.error("check không tách được: %s", exc)
        return False
    if not argv:
        log.error("check rỗng")
        return False
    env = {**os.environ, "RELEASE_VERSION": version}
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        log.error("check quá %ss: %s", timeout, command)
        return False
    except OSError as exc:
        log.error("không chạy được check %s: %s", argv[0], exc)
        return False
    if result.returncode != 0:
        log.error("check thoát %d: %s", result.returncode, (result.stderr or result.stdout).strip()[-500:])
        return False
    return True


def read_history(root: Path) -> list[str]:
    path = root / ".history"
    return path.read_text().split() if path.exists() else []


def write_history(root: Path, versions: list[str]) -> None:
    tmp = root / f".history.{os.getpid()}"
    tmp.write_text("".join(f"{v}\n" for v in versions))
    os.replace(tmp, root / ".history")


def deploy(args: argparse.Namespace) -> int:
    root, version = args.root, args.version
    source = args.source
    if not source.is_dir():
        log.error("không thấy thư mục nguồn %s", source)
        return 1
    releases = root / "releases"
    target = releases / version
    previous = current_version(root)
    if previous == version:
        log.info("%s đang là bản hiện tại, không làm gì", version)
        return 0
    if args.dry_run:
        action = "dùng lại" if target.is_dir() else f"chép từ {source}"
        log.info("[dry-run] %s releases/%s, chuyển current %s -> %s", action, version, previous, version)
        if args.check:
            log.info("[dry-run] sẽ chạy check: %s", args.check)
        return 0
    releases.mkdir(parents=True, exist_ok=True)
    if target.is_dir():
        log.info("releases/%s đã có, dùng lại", version)
    else:
        staging = releases / f".{version}.tmp-{os.getpid()}"
        shutil.rmtree(staging, ignore_errors=True)
        try:
            shutil.copytree(source, staging, symlinks=True)
            staging.rename(target)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        log.info("đã chép %s vào releases/%s", source, version)
    switch(root, version)
    log.info("current: %s -> %s", previous, version)
    if args.check and not run_check(args.check, target, version, args.check_timeout):
        switch(root, previous)
        log.error("check hỏng, đã chuyển current về %s", previous)
        return 1
    write_history(root, [*read_history(root), version])
    log.info("deploy %s xong", version)
    return 0


def rollback(args: argparse.Namespace) -> int:
    root = args.root
    history = read_history(root)
    if len(history) < 2:
        log.error("không có bản trước để rollback")
        return 1
    target = history[-2]
    if not (root / "releases" / target).is_dir():
        log.error("releases/%s không còn, không rollback được", target)
        return 1
    if args.dry_run:
        log.info("[dry-run] chuyển current %s -> %s", history[-1], target)
        return 0
    switch(root, target)
    write_history(root, history[:-1])
    log.info("rollback: current -> %s", target)
    return 0


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
    if args.command == "deploy" and not VERSION.fullmatch(args.version):
        parser.error(f"version không hợp lệ: {args.version!r} (chỉ chữ, số, '.', '_', '-', không bắt đầu bằng dấu)")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
