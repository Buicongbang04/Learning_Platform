"""Đồng bộ một share SMB của khách vào inbox của quillo (bản đầu: chép hết mỗi lần chạy)."""

import argparse
import json
import sys
from pathlib import Path

import smbclient


def copy_tree(root: str, port: int, rel: str, inbox: Path, report: dict) -> None:
    folder = root + ("\\" + rel.replace("/", "\\") if rel else "")
    for entry in smbclient.scandir(folder, port=port):
        path = f"{rel}/{entry.name}" if rel else entry.name
        if entry.is_dir():
            copy_tree(root, port, path, inbox, report)
            continue
        target = inbox / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with smbclient.open_file(root + "\\" + path.replace("/", "\\"), mode="rb", port=port) as source:
            target.write_bytes(source.read())
        report["added"].append(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("--server", "--share", "--user", "--password-file", "--inbox", "--state"):
        parser.add_argument(flag, required=True)
    parser.add_argument("--port", type=int, default=445)
    args = parser.parse_args()
    password = Path(args.password_file).read_text(encoding="utf-8").strip()
    smbclient.register_session(args.server, username=args.user, password=password, port=args.port)
    report = {"added": [], "updated": [], "deleted": [], "errors": []}
    copy_tree(f"\\\\{args.server}\\{args.share}", args.port, "", Path(args.inbox), report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
