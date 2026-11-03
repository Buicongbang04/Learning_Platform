import json
import sys
from pathlib import Path


def make_manifest(root: Path) -> dict:
    """{"files": {đường dẫn tương đối dạng POSIX: {"sha256": hex, "size": byte}}} cho mọi tệp trong `root`."""
    raise NotImplementedError("TODO: duyệt cây thư mục, băm từng tệp, bỏ manifest.json, từ chối symlink")


def verify_manifest(root: Path, manifest: dict) -> list[str]:
    """Danh sách vấn đề của `root` so với `manifest`; rỗng nghĩa là bundle nguyên vẹn."""
    raise NotImplementedError("TODO: thiếu, thừa, sai sha256, đường dẫn không an toàn")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("make", "verify"):
        print("Cách dùng: python manifest.py make <thư mục> | verify <thư mục>", file=sys.stderr)
        return 2
    root = Path(argv[1])
    if argv[0] == "make":
        (root / "manifest.json").write_text(json.dumps(make_manifest(root), indent=2) + "\n")
        return 0
    problems = verify_manifest(root, json.loads((root / "manifest.json").read_text()))
    print("\n".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
