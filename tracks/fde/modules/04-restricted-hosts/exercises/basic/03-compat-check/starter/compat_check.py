import json
import sys
from pathlib import Path

import yaml


def check_host(host_dir: Path, requirements: dict) -> list[dict]:
    """Đọc ldd.txt, python3.txt, os-release trong host_dir; trả danh sách vấn đề {"code", "found"} so với requirements."""
    raise NotImplementedError("TODO: glibc, python, os, eol theo quy tắc trong README")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Cách dùng: python compat_check.py <requirements.yaml> <thư mục máy>...", file=sys.stderr)
        return 2
    requirements = yaml.safe_load(Path(argv[0]).read_text(encoding="utf-8"))
    raise NotImplementedError("TODO: in JSON {tên thư mục máy: [vấn đề]} ra stdout, mã thoát theo README")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
