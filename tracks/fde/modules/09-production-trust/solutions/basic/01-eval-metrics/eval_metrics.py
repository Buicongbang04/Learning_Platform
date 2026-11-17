"""Chỉ số eval của quillo trên nhãn CUAD: precision trích dẫn, recall điều khoản, tỉ lệ từ chối đúng/sai."""

import json
import sys

MIN_OVERLAP = 50
BARE_REFUSALS = {"no", "none", "n/a"}
REFUSAL_PHRASES = (
    "i don't know", "i do not know", "does not contain", "doesn't contain", "do not contain", "not mentioned",
    "no information", "cannot find", "can't find", "not specified", "not provided", "no mention", "there is no",
    "not found", "no documents have been ingested",
)


def is_refusal(answer: str) -> bool:
    text = answer.lower().replace("’", "'").strip()
    if text.rstrip(".!?,;: ") in BARE_REFUSALS:
        return True
    return any(phrase in text for phrase in REFUSAL_PHRASES)


def correct(citation: dict, item: dict) -> bool:
    if citation["contract"] != item["contract"]:
        return False
    for start, end in item["gold"]:
        overlap = min(end, citation["end"]) - max(start, citation["start"])
        if overlap >= min(end - start, MIN_OVERLAP):
            return True
    return False


def ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def evaluate(items: list[dict]) -> dict:
    answerable = [i for i in items if i["gold"]]
    unanswerable = [i for i in items if not i["gold"]]
    cited = right = 0
    found: set[str] = set()
    for item in items:
        if is_refusal(item["answer"]):
            continue
        marks = [correct(c, item) for c in item["citations"]]
        cited += len(marks)
        right += sum(marks)
        if item["gold"] and any(marks):
            found.add(item["id"])
    per_clause: dict[str, dict] = {}
    for item in items:
        row = per_clause.setdefault(item["clause"], {"items": 0, "answerable": 0, "found": 0})
        row["items"] += 1
        row["answerable"] += bool(item["gold"])
        row["found"] += item["id"] in found
    return {
        "items": len(items),
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "citation_precision": ratio(right, cited),
        "clause_recall": ratio(len(found), len(answerable)),
        "correct_refusal_rate": ratio(sum(is_refusal(i["answer"]) for i in unanswerable), len(unanswerable)),
        "false_refusal_rate": ratio(sum(is_refusal(i["answer"]) for i in answerable), len(answerable)),
        "per_clause": dict(sorted(per_clause.items())),
    }


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
