import argparse
import json
import sys
from pathlib import Path


def decide(challenger, champion, min_improvement):
    """Trả (đạt, lý do). TODO: thay phần này."""
    return True, "TODO"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-improvement", type=float, default=0.01)
    args = parser.parse_args()
    challenger = json.loads(Path("models/metrics.json").read_text())
    champion_file = Path("champion/metrics.json")
    champion = json.loads(champion_file.read_text()) if champion_file.is_file() else None
    ok, reason = decide(challenger, champion, args.min_improvement)
    print(("GATE PASSED: " if ok else "GATE FAILED: ") + reason)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
