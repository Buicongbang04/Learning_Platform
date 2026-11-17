"""Bộ red-team prompt injection qua tài liệu: sinh tài liệu tấn công có canary, chấm câu trả lời của quillo."""

import argparse
import json
import sys
from pathlib import Path


def generate(seed: int) -> list[dict]:
    raise NotImplementedError


def grade(attacks: list[dict], answers: list[dict]) -> dict:
    raise NotImplementedError


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--seed", type=int, required=True)
    gen.add_argument("--out", type=Path, required=True)
    grd = sub.add_parser("grade")
    grd.add_argument("--attacks", type=Path, required=True)
    grd.add_argument("--answers", type=Path, required=True)
    args = parser.parse_args(argv[1:])
    if args.command == "generate":
        attacks = generate(args.seed)
        args.out.mkdir(parents=True, exist_ok=True)
        for attack in attacks:
            (args.out / attack["file"]).write_text(attack["content"], encoding="utf-8")
        (args.out / "attacks.json").write_text(json.dumps(attacks, ensure_ascii=False, indent=1) + "\n",
                                               encoding="utf-8")
        return 0
    attacks = json.loads(args.attacks.read_text(encoding="utf-8"))
    answers = json.loads(args.answers.read_text(encoding="utf-8"))["answers"]
    json.dump(grade(attacks, answers), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
