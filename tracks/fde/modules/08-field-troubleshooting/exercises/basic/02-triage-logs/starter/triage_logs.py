"""Tóm tắt log `docker compose logs --no-color` của quillo: nhóm cảnh báo/lỗi, HTTP 5xx và các đợt sự cố."""

import json
import sys


def triage(lines: list[str]) -> dict:
    raise NotImplementedError


def main(argv: list[str]) -> int:
    lines = []
    for path in argv[1:]:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines.extend(handle)
    json.dump(triage(lines), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
