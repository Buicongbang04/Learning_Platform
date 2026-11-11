"""Đồng bộ một share SMB của khách vào inbox của quillo: chỉ giao tệp mới hoặc đổi nội dung, giữ cây thư mục."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath

import smbclient
from smbprotocol.exceptions import SMBException

IGNORED = {"thumbs.db", "desktop.ini", ".ds_store"}
CHUNK = 1 << 20


def ignored(name: str) -> bool:
    return name.startswith("~$") or name.lower() in IGNORED


def listing(root: str, port: int) -> dict[str, dict]:
    found: dict[str, dict] = {}
    pending = [""]
    while pending:
        rel = pending.pop()
        folder = root + ("\\" + rel.replace("/", "\\") if rel else "")
        for entry in smbclient.scandir(folder, port=port):
            if ignored(entry.name):
                continue
            path = f"{rel}/{entry.name}" if rel else entry.name
            if entry.is_dir():
                pending.append(path)
            elif entry.is_file():
                info = entry.smb_info
                found[path] = {"mtime": info.last_write_time.isoformat(), "size": int(info.end_of_file)}
    return found


def fetch(root: str, port: int, rel: str, staging: Path) -> tuple[Path, str]:
    digest = hashlib.sha256()
    fd, name = tempfile.mkstemp(dir=staging, prefix=".", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as out, smbclient.open_file(root + "\\" + rel.replace("/", "\\"), mode="rb",
                                                              port=port) as source:
            while chunk := source.read(CHUNK):
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name), digest.hexdigest()


def sha256_of(path: Path) -> str | None:
    try:
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError:
        return None


def inside(inbox: Path, rel: str) -> Path:
    parts = PurePosixPath(rel).parts
    if not parts or any(p in {"", ".", ".."} for p in parts) or parts[0] in {"done", "failed"}:
        raise ValueError(f"đường dẫn không hợp lệ: {rel!r}")
    return inbox.joinpath(*parts)


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".state-")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(name, path)


def sync(args: argparse.Namespace, password: str) -> dict:
    smbclient.register_session(args.server, username=args.user, password=password, port=args.port)
    root = f"\\\\{args.server}\\{args.share}"
    inbox = Path(args.inbox)
    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {"files": {}}
    known: dict[str, dict] = state["files"]
    report = {"added": [], "updated": [], "deleted": [], "errors": []}
    current = listing(root, args.port)
    for rel, meta in sorted(current.items()):
        old = known.get(rel)
        if old and old["mtime"] == meta["mtime"] and old["size"] == meta["size"]:
            continue
        try:
            target = inside(inbox, rel)
            temp, digest = fetch(root, args.port, rel, inbox)
        except (SMBException, OSError, ValueError) as error:
            report["errors"].append(rel)
            print(f"không giao được {rel}: {type(error).__name__}", file=sys.stderr)
            continue
        if old and old["sha256"] == digest:
            temp.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp, target)
            report["updated" if old else "added"].append(rel)
        known[rel] = meta | {"sha256": digest}
        save_state(state_path, state)
    for rel in sorted(set(known) - set(current)):
        target = inside(inbox, rel)
        if target.is_file() and sha256_of(target) == known[rel]["sha256"]:
            target.unlink()
        del known[rel]
        report["deleted"].append(rel)
        save_state(state_path, state)
    save_state(state_path, state)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("--server", "--share", "--user", "--password-file", "--inbox", "--state"):
        parser.add_argument(flag, required=True)
    parser.add_argument("--port", type=int, default=445)
    args = parser.parse_args()
    password = Path(args.password_file).read_text(encoding="utf-8").rstrip("\r\n")
    try:
        report = sync(args, password)
    except (SMBException, OSError, ValueError) as error:
        print(f"đồng bộ thất bại: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    finally:
        smbclient.reset_connection_cache()
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
