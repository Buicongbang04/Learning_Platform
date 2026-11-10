import re

import pytest
from sklearn.metrics import f1_score

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("extract.ipynb")


def rec(**kw):
    base = {"sentiment": "negative", "topic": "facility", "aspects": ["máy lạnh"], "actionable": True,
            "suggestion": "Sửa máy lạnh phòng học."}
    base.update(kw)
    return base


# ---------- check_record ----------

def test_check_valid(nb):
    assert nb.check_record(rec()) == []
    assert nb.check_record(rec(sentiment="positive", topic="lecturer", aspects=[], actionable=False,
                               suggestion=None)) == []


@pytest.mark.parametrize("record", [
    None, "không phải dict", rec(sentiment="tiêu cực"), rec(topic="wifi"), rec(aspects=["a", "b", "c", "d"]),
    rec(aspects=["x" * 41]), rec(actionable="yes"), rec(extra=1),
    {k: v for k, v in rec().items() if k != "suggestion"},
])
def test_check_schema_errors(nb, record):
    errors = nb.check_record(record)
    assert errors and all(e.startswith("schema: ") for e in errors), errors


def test_check_schema_stops_before_rules(nb):
    errors = nb.check_record(rec(topic="wifi", actionable=True, suggestion=None))
    assert errors and all(e.startswith("schema: ") for e in errors)


@pytest.mark.parametrize("record, expected", [
    (rec(actionable=True, suggestion=None), ["rule: suggestion"]),
    (rec(actionable=True, suggestion="   "), ["rule: suggestion"]),
    (rec(actionable=False, suggestion="Sửa máy lạnh."), ["rule: suggestion"]),
    (rec(aspects=["Máy lạnh", "máy lạnh "]), ["rule: aspects"]),
    (rec(aspects=["máy lạnh", "  "]), ["rule: aspects"]),
    (rec(actionable=False, suggestion="x", aspects=["a", "A"]), ["rule: suggestion", "rule: aspects"]),
])
def test_check_rules(nb, record, expected):
    assert nb.check_record(record) == expected


# ---------- score_batch ----------

GOLDS = [
    {"sentiment": "negative", "topic": "facility"},
    {"sentiment": "positive", "topic": "lecturer"},
    {"sentiment": "neutral", "topic": "others"},
    {"sentiment": "negative", "topic": "training_program"},
    {"sentiment": "positive", "topic": "lecturer"},
]


def test_score_batch(nb):
    records = [
        rec(),                                                                            # đúng cả hai, actionable
        rec(sentiment="positive", topic="lecturer", aspects=["nhiệt tình"], actionable=False, suggestion=None),
        rec(sentiment="negative", topic="others", aspects=[], actionable=False, suggestion=None),  # sai cảm xúc
        rec(sentiment="negative", topic="training_program", actionable=True, suggestion=None),     # sai quy tắc
        None,                                                                             # JSON hỏng
    ]
    s = nb.score_batch(records, GOLDS)
    assert set(s) == {"n", "valid_rate", "sentiment_acc", "topic_acc", "sentiment_macro_f1", "topic_macro_f1",
                      "actionable_rate"}
    assert s["n"] == 5 and type(s["n"]) is int
    assert s["valid_rate"] == pytest.approx(3 / 5)
    assert s["sentiment_acc"] == pytest.approx(2 / 5)
    assert s["topic_acc"] == pytest.approx(3 / 5)
    assert s["actionable_rate"] == pytest.approx(1 / 3), "trên số câu hợp lệ"
    gs = [g["sentiment"] for g in GOLDS]
    ps = ["negative", "positive", "negative", "none", "none"]
    assert s["sentiment_macro_f1"] == pytest.approx(
        f1_score(gs, ps, labels=nb.LABELS, average="macro", zero_division=0), abs=1e-12)
    gt = [g["topic"] for g in GOLDS]
    pt = ["facility", "lecturer", "others", "none", "none"]
    assert s["topic_macro_f1"] == pytest.approx(
        f1_score(gt, pt, labels=nb.TOPICS, average="macro", zero_division=0), abs=1e-12)
    assert all(isinstance(v, float) for k, v in s.items() if k != "n")


def test_score_batch_all_invalid(nb):
    s = nb.score_batch([None, None], GOLDS[:2])
    assert s["valid_rate"] == 0.0 and s["actionable_rate"] == 0.0 and s["sentiment_macro_f1"] == 0.0


def test_score_batch_rejects(nb):
    with pytest.raises(ValueError):
        nb.score_batch([], [])
    with pytest.raises(ValueError):
        nb.score_batch([None], GOLDS)


# ---------- báo cáo ----------

def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 500, "báo cáo: ít nhất 500 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng kết quả"
