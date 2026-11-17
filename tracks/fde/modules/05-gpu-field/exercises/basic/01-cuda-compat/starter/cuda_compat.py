import json
import sys
from pathlib import Path


def check(host: dict) -> dict:
    """host: driver, cuda, toolkit, compute_capability, access, docker. Trả {"compatible": bool, "issues": [...]}."""
    raise NotImplementedError("TODO: áp bảng tương thích trong README")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Cách dùng: python cuda_compat.py <host.json>", file=sys.stderr)
        return 2
    result = check(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise NotImplementedError("TODO: mã thoát theo README")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
