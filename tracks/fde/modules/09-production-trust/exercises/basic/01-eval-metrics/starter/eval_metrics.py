"""Chỉ số eval của quillo trên nhãn CUAD: precision trích dẫn, recall điều khoản, tỉ lệ từ chối đúng/sai."""

import json
import sys


def evaluate(items: list[dict]) -> dict:
    raise NotImplementedError


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Dùng: python eval_metrics.py <fixture.json>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        items = json.load(handle)["items"]
    json.dump(evaluate(items), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
