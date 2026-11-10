import argparse
import json
import math
import sys
from pathlib import Path

EPSILON = 1e-12


def decide(challenger, champion, min_improvement):
    new = challenger.get("mae") if isinstance(challenger, dict) else None
    if not isinstance(new, (int, float)) or isinstance(new, bool) or not math.isfinite(new):
        return False, f"challenger không có mae hữu hạn ({new!r})"
    if champion is None:
        return True, f"chưa có champion, nhận challenger (mae {new:.2f})"
    old = champion.get("mae")
    if not isinstance(old, (int, float)) or isinstance(old, bool) or not math.isfinite(old):
        return False, f"champion không có mae hữu hạn ({old!r})"
    needed = old * (1 - min_improvement)
    if new <= needed + EPSILON:
        return True, f"challenger {new:.2f} <= {needed:.2f} (champion {old:.2f}, cải thiện tối thiểu {min_improvement:.0%})"
    return False, f"challenger {new:.2f} > {needed:.2f} (champion {old:.2f}, cải thiện tối thiểu {min_improvement:.0%})"


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
