import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("model_scorecard.ipynb")


Y_TRUE = [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
Y_PRED = [1, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def test_confusion_table(nb):
    cm = nb.confusion_table(Y_TRUE, Y_PRED)
    assert cm.index.name == "actual" and cm.columns.name == "predicted"
    assert list(cm.index) == [0, 1] and list(cm.columns) == [0, 1]
    assert cm.values.tolist() == [[6, 1], [2, 1]]                      # TN FP / FN TP
    assert all(dtype.kind == "i" for dtype in cm.dtypes)


def test_confusion_table_all_cells_and_inputs(nb):
    cm = nb.confusion_table(pd.Series([0, 0, 1]), np.zeros(3, dtype=int))  # model không bao giờ đoán 1
    assert cm.values.tolist() == [[2, 0], [1, 0]]
    cm = nb.confusion_table(np.array([True, False]), [True, True])         # bool cũng được
    assert cm.values.tolist() == [[0, 1], [0, 1]]
    with pytest.raises(ValueError):
        nb.confusion_table([0, 1, 1], [0, 1])


def test_scorecard(nb):
    s = nb.scorecard(Y_TRUE, Y_PRED)
    assert set(s) == {"n", "accuracy", "baseline_accuracy", "precision", "recall", "flagged_share"}
    assert s["n"] == 10 and isinstance(s["n"], int)
    assert s["accuracy"] == pytest.approx(0.7)
    assert s["baseline_accuracy"] == pytest.approx(0.7)                  # luôn đoán 0 cũng đúng 70%
    assert s["precision"] == pytest.approx(0.5)
    assert s["recall"] == pytest.approx(1 / 3)
    assert s["flagged_share"] == pytest.approx(0.2)


def test_scorecard_edge_cases(nb):
    s = nb.scorecard([1, 1, 0], [0, 0, 0])                               # không gắn cờ ai
    assert s["precision"] == 0.0 and s["recall"] == 0.0 and s["flagged_share"] == 0.0
    assert s["baseline_accuracy"] == pytest.approx(2 / 3)               # lớp đông nhất là 1
    s = nb.scorecard([0, 0], [0, 1])                                     # không có ca dương
    assert s["recall"] == 0.0 and s["accuracy"] == pytest.approx(0.5)


def test_threshold_table(nb):
    y = [1, 0, 1, 0, 0]
    score = [0.9, 0.8, 0.4, 0.3, 0.1]
    out = nb.threshold_table(y, score, [0.5, 0.3, 0.95])
    assert list(out.columns) == ["threshold", "flagged", "tp", "precision", "recall", "accuracy"]
    assert out["threshold"].tolist() == [0.5, 0.3, 0.95]                # giữ thứ tự đầu vào
    assert out["flagged"].tolist() == [2, 4, 0]                         # score >= ngưỡng: 0.3 được tính
    assert out["tp"].tolist() == [1, 2, 0]
    assert out["precision"].tolist() == pytest.approx([0.5, 0.5, 0.0])
    assert out["recall"].tolist() == pytest.approx([0.5, 1.0, 0.0])
    assert out["accuracy"].tolist() == pytest.approx([0.6, 0.6, 0.6])


@pytest.fixture(scope="module")
def telco():
    raw = pd.read_csv(ex.dataset("telco-churn") / "WA_Fn-UseC_-Telco-Customer-Churn.csv")
    return raw, (raw.Churn == "Yes").astype(int)


def test_real_baselines(nb, telco):
    raw, y = telco
    always = nb.scorecard(y, np.zeros(len(y), dtype=int))
    assert always["n"] == 7043
    assert always["accuracy"] == pytest.approx(0.7346, abs=1e-4)
    assert always["recall"] == 0.0
    two_year = raw.Contract == "Two year"
    assert nb.scorecard(y[two_year], np.zeros(two_year.sum(), dtype=int))["accuracy"] == pytest.approx(0.9717, abs=1e-4)


def test_real_rule(nb, telco):
    raw, y = telco
    rule = ((raw.Contract == "Month-to-month") & (raw.tenure <= 12)).astype(int)
    assert nb.confusion_table(y, rule).values.tolist() == [[4204, 970], [845, 1024]]
    s = nb.scorecard(y, rule)
    assert s["precision"] == pytest.approx(0.5135, abs=1e-4)
    assert s["recall"] == pytest.approx(0.5479, abs=1e-4)
    assert s["flagged_share"] == pytest.approx(0.2831, abs=1e-4)
