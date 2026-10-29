import math

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

Y = [1, 0, 1, 0, 0, 1, 0, 0]
S = [0.9, 0.8, 0.7, 0.5, 0.4, 0.3, 0.2, 0.1]


@pytest.fixture(scope="module")
def budget():
    return ex.module("budget.py")


def test_k_from_budget(budget):
    assert budget.k_from_budget(100, 0.5, 1000) == 200
    assert budget.k_from_budget(99.9, 5, 1000) == 19
    assert budget.k_from_budget(1000, 0.5, 120) == 120
    assert isinstance(budget.k_from_budget(10, 3, 50), int)


def test_precision_recall_by_hand(budget):
    assert budget.precision_at_k(Y, S, 1) == pytest.approx(1.0)
    assert budget.precision_at_k(Y, S, 3) == pytest.approx(2 / 3)
    assert budget.recall_at_k(Y, S, 3) == pytest.approx(2 / 3)
    assert budget.precision_at_k(Y, S, 6) == pytest.approx(3 / 6)
    assert budget.recall_at_k(Y, S, 6) == pytest.approx(1.0)
    # thứ tự đầu vào không quan trọng
    order = [7, 3, 0, 5, 1, 6, 2, 4]
    assert budget.precision_at_k(np.array(Y)[order], np.array(S)[order], 3) == pytest.approx(2 / 3)


def test_k_larger_than_n_and_invalid_k(budget):
    assert budget.precision_at_k(Y, S, 100) == pytest.approx(3 / 8)
    assert budget.recall_at_k(Y, S, 100) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        budget.precision_at_k(Y, S, 0)
    with pytest.raises(ValueError):
        budget.recall_at_k(Y, S, 0)
    assert math.isnan(budget.recall_at_k([0, 0, 0], [0.3, 0.2, 0.1], 2))


def test_random_scores_give_prevalence_and_perfect_scores_give_one(budget):
    precisions = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        y = (rng.random(2000) < 0.1).astype(int)
        precisions.append(budget.precision_at_k(y, rng.random(2000), 200))
    assert np.mean(precisions) == pytest.approx(0.1, abs=0.015)
    rng = np.random.default_rng(0)
    y = (rng.random(2000) < 0.1).astype(int)
    perfect = y + rng.random(2000) * 0.5
    assert budget.precision_at_k(y, perfect, int(y.sum())) == pytest.approx(1.0)
    assert budget.recall_at_k(y, perfect, int(y.sum())) == pytest.approx(1.0)


def test_weekly_at_k_by_hand(budget):
    df = pd.DataFrame({
        "week": ["w2", "w2", "w2", "w1", "w1", "w1", "w1", "w3"],
        "score": [0.9, 0.2, 0.5, 0.8, 0.7, 0.1, 0.6, 0.3],
        "label": [1, 1, 0, 0, 1, 1, 0, 1],
    })
    out = budget.weekly_at_k(df, k=2)
    assert list(out.index) == ["w1", "w2", "w3"]
    assert out.loc["w1", "n"] == 4 and out.loc["w1", "positives"] == 2
    assert out.loc["w1", "selected"] == 2 and out.loc["w1", "hits"] == 1
    assert out.loc["w1", "precision"] == pytest.approx(0.5)
    assert out.loc["w1", "recall"] == pytest.approx(0.5)
    assert out.loc["w2", "precision"] == pytest.approx(0.5)
    assert out.loc["w3", "selected"] == 1 and out.loc["w3", "precision"] == pytest.approx(1.0)


def test_weekly_pooled_precision_is_consistent(budget):
    rng = np.random.default_rng(3)
    n = 3000
    df = pd.DataFrame({"wk": rng.integers(0, 20, n), "s": rng.random(n)})
    df["y"] = (rng.random(n) < df.s * 0.3).astype(int)
    out = budget.weekly_at_k(df, k=25, week_col="wk", score_col="s", label_col="y")
    assert len(out) == 20
    assert out.selected.sum() == 20 * 25
    manual = sum(g.nlargest(25, "s").y.sum() for _, g in df.groupby("wk"))
    assert out.hits.sum() == manual
