import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "cuad-eval.json"
EXPECTED = HERE / "expected" / "cuad-eval.json"
KEYS = ("items", "answerable", "unanswerable", "citation_precision", "clause_recall", "correct_refusal_rate",
        "false_refusal_rate", "per_clause")


def items() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["items"]


def evaluate(data: list[dict]) -> dict:
    result = ex.module("eval_metrics.py").evaluate(json.loads(json.dumps(data)))
    assert isinstance(result, dict), "evaluate() phải trả dict"
    return result


def compare(got: dict, want: dict, label: str) -> None:
    for key in KEYS:
        assert key in got, f"{label}: thiếu khoá {key!r}"
        if isinstance(want[key], float):
            assert isinstance(got[key], (int, float)) and abs(got[key] - want[key]) < 1e-4, \
                f"{label}: {key} = {got[key]!r}, cần {want[key]}"
        else:
            assert got[key] == want[key], f"{label}: {key} = {got[key]!r}, cần {want[key]!r}"


def item(n: int, gold: list, answer: str, citations: list, clause: str = "Governing Law",
         contract: str = "C1") -> dict:
    return {"id": f"q{n}", "contract": contract, "clause": clause, "question": "?", "gold": gold, "answer": answer,
            "citations": [{"contract": c, "chunk": 0, "start": s, "end": e} for c, s, e in citations]}


def test_recorded_answers():
    compare(evaluate(items()), json.loads(EXPECTED.read_text(encoding="utf-8")), "fixture CUAD")


def test_same_result_after_renaming_and_shifting():
    rng = random.Random()
    data = items()
    rng.shuffle(data)
    names = {c: f"contract-{rng.randrange(10**6)}-{i}" for i, c in enumerate(sorted({i["contract"] for i in data}))}
    shift = {c: rng.randrange(0, 5000) for c in names}
    for row in data:
        row["id"] = f"x-{rng.randrange(10**9)}-{row['id']}"
        row["gold"] = [[s + shift[row["contract"]], e + shift[row["contract"]]] for s, e in row["gold"]]
        for c in row["citations"]:
            c["start"] += shift[c["contract"]]
            c["end"] += shift[c["contract"]]
            c["contract"] = names[c["contract"]]
        row["contract"] = names[row["contract"]]
    compare(evaluate(data), json.loads(EXPECTED.read_text(encoding="utf-8")), "fixture đổi tên, dời vị trí, xáo thứ tự")


CASES = [
    ("chồng 50 ký tự là đúng", [item(1, [[100, 400]], "Delaware law.", [("C1", 350, 1300)])],
     {"citation_precision": 1.0, "clause_recall": 1.0}),
    ("chồng 49 ký tự là sai", [item(1, [[100, 400]], "Delaware law.", [("C1", 351, 1300)])],
     {"citation_precision": 0.0, "clause_recall": 0.0}),
    ("nhãn ngắn phải nằm trọn", [item(1, [[500, 520]], "1 May 2020", [("C1", 0, 515)]),
                                 item(2, [[500, 520]], "1 May 2020", [("C1", 500, 1500)], contract="C1")],
     {"citation_precision": 0.5, "clause_recall": 0.5}),
    ("đúng vị trí nhưng sai hợp đồng", [item(1, [[100, 400]], "Delaware law.", [("C2", 0, 1000), ("C1", 0, 1000)])],
     {"citation_precision": 0.5, "clause_recall": 1.0}),
    ("trả lời câu không có nhãn: trích dẫn đều sai", [item(1, [], "It is capped at $1M.", [("C1", 0, 1000)])],
     {"citation_precision": 0.0, "clause_recall": None, "correct_refusal_rate": 0.0}),
    ("từ chối: trích dẫn không tính", [item(1, [[100, 400]], "I don’t know.", [("C1", 0, 1000)]),
                                      item(2, [], "The passages do not contain this.", [("C1", 0, 1000)])],
     {"citation_precision": None, "clause_recall": 0.0, "correct_refusal_rate": 1.0, "false_refusal_rate": 1.0}),
    ("'No.' là từ chối, 'No cap applies' thì không", [item(1, [], "No.", [("C1", 0, 1000)]),
                                                    item(2, [], "No cap applies to fees.", [("C1", 0, 1000)])],
     {"correct_refusal_rate": 0.5, "citation_precision": 0.0}),
    ("không trích dẫn nào", [item(1, [[0, 10]], "Delaware.", [])],
     {"citation_precision": None, "clause_recall": 0.0, "false_refusal_rate": 0.0}),
]


@pytest.mark.parametrize("label,data,want", CASES, ids=[c[0] for c in CASES])
def test_rules(label, data, want):
    got = evaluate(data)
    for key, value in want.items():
        assert key in got, f"{label}: thiếu khoá {key!r}"
        if value is None:
            assert got[key] is None, f"{label}: {key} = {got[key]!r}, cần null (mẫu số bằng 0)"
        else:
            assert got[key] is not None and abs(got[key] - value) < 1e-4, f"{label}: {key} = {got[key]!r}, cần {value}"


def test_per_clause_counts():
    data = [item(1, [[0, 100]], "x", [("C1", 0, 100)], clause="Insurance"),
            item(2, [], "I do not know", [], clause="Insurance"),
            item(3, [[0, 100]], "x", [("C1", 500, 900)], clause="Audit Rights")]
    got = evaluate(data)["per_clause"]
    assert got == {"Audit Rights": {"items": 1, "answerable": 1, "found": 0},
                   "Insurance": {"items": 2, "answerable": 1, "found": 1}}, f"per_clause sai: {got}"


def test_cli_prints_same_json(tmp_path):
    try:
        done = run_sandboxed([sys.executable, str(ex.path("eval_metrics.py")), str(FIXTURE)], writable=[tmp_path],
                             cwd=tmp_path, env={}, timeout=30)
    except subprocess.TimeoutExpired:
        pytest.fail("eval_metrics.py chạy quá 30 s")
    assert done.returncode == 0, f"eval_metrics.py thoát {done.returncode}\n{done.stderr[-2000:]}"
    try:
        got = json.loads(done.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"stdout không phải JSON: {error}\n{done.stdout[:500]}")
    compare(got, json.loads(EXPECTED.read_text(encoding="utf-8")), "CLI")
