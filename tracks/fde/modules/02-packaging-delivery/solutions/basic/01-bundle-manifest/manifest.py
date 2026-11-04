import hashlib
import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath

MANIFEST = "manifest.json"
CHUNK = 1 << 20


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK):
            sha.update(chunk)
    return sha.hexdigest()


def _walk(root: Path) -> dict[str, Path]:
    found = {}
    for top, dirs, names in os.walk(root):
        for name in dirs + names:
            path = Path(top) / name
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                continue
            rel = path.relative_to(root).as_posix()
            if stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                found[rel] = path
            else:
                raise ValueError(f"tệp đặc biệt trong bundle: {rel}")
    found.pop(MANIFEST, None)
    return found


def make_manifest(root: Path) -> dict:
    """{"files": {đường dẫn tương đối dạng POSIX: {"sha256": hex, "size": byte}}} cho mọi tệp trong `root`."""
    root = Path(root)
    files = {}
    for rel, path in sorted(_walk(root).items()):
        if path.is_symlink():
            raise ValueError(f"symlink trong bundle: {rel}")
        files[rel] = {"sha256": _sha256(path), "size": path.stat().st_size}
    return {"files": files}


def _safe(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def verify_manifest(root: Path, manifest: dict) -> list[str]:
    """Danh sách vấn đề của `root` so với `manifest`; rỗng nghĩa là bundle nguyên vẹn."""
    root = Path(root)
    expected = manifest["files"]
    present = _walk(root)
    problems = []
    for name, meta in sorted(expected.items()):
        if not _safe(name):
            problems.append(f"đường dẫn không an toàn: {name}")
            continue
        path = present.get(name)
        if path is None:
            problems.append(f"thiếu: {name}")
        elif path.is_symlink() or path.stat().st_size != meta["size"] or _sha256(path) != meta["sha256"]:
            problems.append(f"sai sha256: {name}")
    problems += [f"thừa: {name}" for name in sorted(set(present) - set(expected))]
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("make", "verify"):
        print("Cách dùng: python manifest.py make <thư mục> | verify <thư mục>", file=sys.stderr)
        return 2
    root = Path(argv[1])
    if argv[0] == "make":
        (root / MANIFEST).write_text(json.dumps(make_manifest(root), indent=2) + "\n")
        return 0
    problems = verify_manifest(root, json.loads((root / MANIFEST).read_text()))
    print("\n".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
