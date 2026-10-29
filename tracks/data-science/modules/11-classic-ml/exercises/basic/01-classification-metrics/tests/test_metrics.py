import ast

import numpy as np
import pytest
from sklearn import metrics as skm

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def m():
    return ex.module("metrics.py")


def sample(seed: int, n: int = 400, prevalence: float = 0.15, ties: bool = False):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < prevalence).astype(int)
    score = rng.normal(0, 1, n) + 1.2 * y
    if ties:
        score = np.round(score, 1)   # nhiều điểm trùng nhau, như output của cây quyết định
    return y, score


def test_confusion_counts(m):
    y = [1, 1, 0, 0, 1, 0, 0]
    pred = [1, 0, 1, 0, 1, 0, 0]
    assert m.confusion_counts(y, pred) == {"tp": 2, "fp": 1, "fn": 1, "tn": 3}
    # tự cài, không dùng sklearn trong bài này
    tree = ast.parse(ex.read("metrics.py"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    assert not any(name.startswith("sklearn") for name in names)


def test_precision_recall_f1(m):
    y = [1, 1, 0, 0, 1, 0, 0]
    pred = [1, 0, 1, 0, 1, 0, 0]
    p, r, f1 = m.precision_recall_f1(y, pred)
    assert p == pytest.approx(2 / 3) and r == pytest.approx(2 / 3) and f1 == pytest.approx(2 / 3)


def test_precision_when_nothing_predicted_is_zero(m):
    p, r, f1 = m.precision_recall_f1([1, 0, 1], [0, 0, 0])
    assert (p, r, f1) == (0.0, 0.0, 0.0)


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("ties", [False, True])
def test_roc_auc_matches_sklearn(m, seed, ties):
    y, s = sample(seed, ties=ties)
    assert m.roc_auc(y, s) == pytest.approx(skm.roc_auc_score(y, s), abs=1e-9)


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("ties", [False, True])
def test_average_precision_matches_sklearn(m, seed, ties):
    y, s = sample(seed, ties=ties)
    assert m.average_precision(y, s) == pytest.approx(skm.average_precision_score(y, s), abs=1e-9)


def test_roc_auc_ignores_monotone_transform_but_log_loss_does_not(m):
    y, s = sample(11)
    p = 1 / (1 + np.exp(-s))
    assert m.roc_auc(y, p) == pytest.approx(m.roc_auc(y, p**4))
    assert m.log_loss(y, p) != pytest.approx(m.log_loss(y, p**4), rel=0.01)


def test_random_scores_baselines(m):
    rng = np.random.default_rng(3)
    y = (rng.random(50_000) < 0.1).astype(int)
    s = rng.random(50_000)
    assert m.roc_auc(y, s) == pytest.approx(0.5, abs=0.02)
    # PR-AUC của model ngẫu nhiên bằng prevalence, không phải 0.5
    assert m.average_precision(y, s) == pytest.approx(y.mean(), abs=0.01)


def test_log_loss_matches_sklearn_and_clips(m):
    y, s = sample(5)
    p = 1 / (1 + np.exp(-s))
    assert m.log_loss(y, p) == pytest.approx(skm.log_loss(y, p), rel=1e-9)
    value = m.log_loss([1, 0], [0.0, 0.0])        # p = 0 cho một ca dương: phải hữu hạn nhờ clip
    assert np.isfinite(value) and value > 10
