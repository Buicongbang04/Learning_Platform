import unicodedata

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
LABELS = ["giảng viên", "chương trình đào tạo", "cơ sở vật chất", "khác"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("benchmark.ipynb")


def test_stratified_sample(nb):
    df = pd.DataFrame({"text": [f"câu {i}" for i in range(20)], "topic": [2] * 8 + [0] * 9 + [3] * 3},
                      index=range(100, 120))
    out = nb.stratified_sample(df, "topic", 4, seed=0)
    assert out["topic"].tolist() == [0] * 4 + [2] * 4 + [3] * 3, "nhãn tăng dần, nhãn ít hơn n thì lấy hết"
    expected = pd.concat([df[df.topic == c].sample(n=min(4, (df.topic == c).sum()), random_state=0)
                          for c in [0, 2, 3]])
    assert out.index.tolist() == expected.index.tolist(), "group.sample(n, random_state=seed), giữ index gốc"
    again = nb.stratified_sample(df, "topic", 4, seed=0)
    assert again.index.tolist() == out.index.tolist()
    assert nb.stratified_sample(df, "topic", 4, seed=1).index.tolist() != out.index.tolist()


@pytest.mark.parametrize("reply, expected", [
    ("giảng viên", "giảng viên"),
    ("Giảng viên.", "giảng viên"),
    ("  **Cơ sở vật chất**\n", "cơ sở vật chất"),
    ("Nhãn: chương trình đào tạo", "chương trình đào tạo"),
    ('"khác"', "khác"),
    ("Câu này nói về cơ sở vật chất của trường.", "cơ sở vật chất"),
    ("giảng viên hoặc chương trình đào tạo", None),
    ("không rõ", None),
    ("khách sạn", None),
    ("", None),
])
def test_parse_label(nb, reply, expected):
    assert nb.parse_label(reply, LABELS) == expected


def test_parse_label_nfd_and_returns_original(nb):
    nfd = unicodedata.normalize("NFD", "Giảng Viên")
    assert nb.parse_label(nfd, LABELS) == "giảng viên"
    assert nb.parse_label("POSITIVE", ["Positive", "Negative"]) == "Positive", "trả nhãn đúng dạng trong labels"


def test_macro_f1_by_hand(nb):
    y_true = ["a", "a", "b", "b", "c"]
    y_pred = ["a", "b", "b", None, "a"]
    # a: tp 1, fp 1, fn 1 -> 0.5 ; b: tp 1, fp 1, fn 1 -> 0.5 ; c: tp 0 -> 0
    assert nb.macro_f1(y_true, y_pred, ["a", "b", "c"]) == pytest.approx(1 / 3)
    assert nb.macro_f1(["a", "b"], ["a", "b"], ["a", "b"]) == pytest.approx(1.0)
    assert nb.macro_f1(["a", "a"], [None, None], ["a", "b"]) == 0.0


def test_macro_f1_matches_sklearn(nb):
    from sklearn.metrics import f1_score

    rng = np.random.default_rng(0)
    y_true = list(rng.choice(LABELS, 200))
    y_pred = [p if rng.random() > 0.1 else None for p in rng.choice(LABELS, 200)]
    ref = f1_score(y_true, [p or "__none__" for p in y_pred], labels=LABELS, average="macro", zero_division=0)
    assert nb.macro_f1(y_true, y_pred, LABELS) == pytest.approx(ref)


def test_latency_summary(nb):
    s = nb.latency_summary([1.0, 2.0, 3.0, 4.0, 10.0])
    assert s == pytest.approx({"p50": 3.0, "p95": 8.8, "mean": 4.0})
    assert all(type(v) is float for v in s.values())
