"""Acceptance test chạy cùng khách: health, độ trễ p95 của /api/ask, câu trả lời có trích dẫn, ACL theo thư mục."""

import argparse
import json
import sys
from pathlib import Path


def run(cfg: dict) -> dict:
    raise NotImplementedError


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv[1:])
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    report = run(cfg)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
