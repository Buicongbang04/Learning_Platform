import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("explain.ipynb")


def make_data(n: int = 3000, seed: int = 0) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=n)
    weak = rng.normal(size=n)
    X = pd.DataFrame({
        "signal": signal,
        "copy": signal + rng.normal(0, 0.05, n),   # gần như trùng với signal
        "weak": weak,
        "noise": rng.normal(size=n),
    })
    y = (rng.random(n) < 1 / (1 + np.exp(-(2.0 * signal + 0.5 * weak)))).astype(int)
    return X, y


def test_structure_and_order(nb):
    X, y = make_data()
    model = LogisticRegression().fit(X, y)
    out = nb.permutation_importance_df(model, X, y, roc_auc_score, n_repeats=5, seed=0)
    assert set(out.index) == set(X.columns)
    assert list(out.columns[:2]) == ["importance_mean", "importance_std"]
    assert out.importance_mean.is_monotonic_decreasing
    assert (out.importance_std >= 0).all()


def test_noise_near_zero_weak_positive(nb):
    X, y = make_data(seed=1)
    model = LogisticRegression().fit(X, y)
    out = nb.permutation_importance_df(model, X, y, roc_auc_score, n_repeats=5, seed=0)
    assert abs(out.loc["noise", "importance_mean"]) < 0.01
    assert out.loc["weak", "importance_mean"] > 0.01


def test_correlated_features_share_importance(nb):
    X, y = make_data(seed=2)
    alone = LogisticRegression().fit(X.drop(columns="copy"), y)
    both = LogisticRegression().fit(X, y)
    imp_alone = nb.permutation_importance_df(alone, X.drop(columns="copy"), y, roc_auc_score, 5, 0)
    imp_both = nb.permutation_importance_df(both, X, y, roc_auc_score, 5, 0)
    # có bản sao thì model chia trọng số cho hai cột: hoán vị một cột chỉ mất một phần thông tin,
    # nên ít nhất một trong hai trông "kém quan trọng" hơn hẳn so với khi signal đứng một mình
    weaker = min(imp_both.loc["signal", "importance_mean"], imp_both.loc["copy", "importance_mean"])
    assert weaker < 0.5 * imp_alone.loc["signal", "importance_mean"]


def test_reproducible_and_does_not_mutate(nb):
    X, y = make_data(seed=3)
    before = X.copy()
    model = LogisticRegression().fit(X, y)
    a = nb.permutation_importance_df(model, X, y, roc_auc_score, n_repeats=3, seed=7)
    b = nb.permutation_importance_df(model, X, y, roc_auc_score, n_repeats=3, seed=7)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(X, before)


def test_group_shap_sums_one_hot_columns(nb):
    values = pd.DataFrame(
        [[0.1, 0.2, -0.3, 0.05, 0.4], [0.0, -0.1, 0.2, 0.0, -0.4]],
        columns=["num__tenure", "cat__InternetService_DSL", "cat__InternetService_Fiber optic",
                 "cat__Internet_x", "cat__Contract_Two year"])
    out = nb.group_shap(values, ["tenure", "Internet", "InternetService", "Contract"])
    assert list(out.columns) == ["tenure", "Internet", "InternetService", "Contract"]
    np.testing.assert_allclose(out["InternetService"], [-0.1, 0.1])     # tên dài nhất khớp được thắng
    np.testing.assert_allclose(out["Internet"], [0.05, 0.0])
    np.testing.assert_allclose(out.sum(axis=1), values.sum(axis=1))     # tổng SHAP không đổi


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 350
