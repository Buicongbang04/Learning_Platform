import numpy as np
import pytest
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("calibration.ipynb")


def calibrated(n: int, seed: int):
    rng = np.random.default_rng(seed)
    p = rng.beta(2, 5, n)
    return (rng.random(n) < p).astype(int), p


def test_reliability_table_matches_sklearn(nb):
    y, p = calibrated(3000, 0)
    table = nb.reliability_table(y, p, n_bins=10)
    frac, mean = calibration_curve(y, p, n_bins=10, strategy="uniform")
    assert list(table.columns[:3]) == ["mean_pred", "frac_pos", "n"]
    np.testing.assert_allclose(table.mean_pred, mean)
    np.testing.assert_allclose(table.frac_pos, frac)
    assert table.n.sum() == 3000


def test_reliability_table_drops_empty_bins(nb):
    table = nb.reliability_table([0, 1, 1, 0], [0.05, 0.92, 0.97, 0.08], n_bins=10)
    assert len(table) == 2
    assert table.n.tolist() == [2, 2]
    assert table.frac_pos.tolist() == [0.0, 1.0]


def test_ece_by_hand(nb):
    # bin [0, 0.5): p 0.1, 0.3 -> mean 0.2, frac 0.5 | bin [0.5, 1]: p 0.9 -> frac 1
    ece = nb.expected_calibration_error([1, 0, 1], [0.1, 0.3, 0.9], n_bins=2)
    assert ece == pytest.approx(2 / 3 * 0.3 + 1 / 3 * 0.1)


def test_ece_small_when_calibrated_large_when_not(nb):
    y, p = calibrated(20000, 1)
    assert nb.expected_calibration_error(y, p) < 0.02
    assert nb.expected_calibration_error(y, np.sqrt(p)) > 0.15


def test_prior_correct_formula(nb):
    assert nb.prior_correct(np.array([0.5]), 0.5, 0.1)[0] == pytest.approx(0.1)
    p = np.array([0.05, 0.3, 0.8])
    np.testing.assert_allclose(nb.prior_correct(p, 0.2, 0.2), p)
    out = nb.prior_correct(p, 0.5, 0.1)
    assert np.all(np.diff(out) > 0) and np.all(out < p)    # giữ thứ hạng, kéo xác suất xuống


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_prior_correct_fixes_class_weight(nb, seed):
    rng = np.random.default_rng(seed)
    n = 20000
    X = rng.normal(size=(n, 3))
    y = (rng.random(n) < 1 / (1 + np.exp(-(-3 + X @ np.array([1.0, -0.8, 0.5]))))).astype(int)
    tr, te = slice(0, n // 2), slice(n // 2, n)
    p_bal = LogisticRegression(class_weight="balanced").fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    fixed = nb.prior_correct(p_bal, 0.5, y[tr].mean())
    assert p_bal.mean() > 2 * y[te].mean()                      # class_weight làm xác suất phình to
    assert fixed.mean() == pytest.approx(y[te].mean(), abs=0.015)
    assert np.mean((fixed - y[te]) ** 2) < np.mean((p_bal - y[te]) ** 2)


@pytest.mark.parametrize("method", ["sigmoid", "isotonic"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_recalibrate_repairs_distorted_scores(nb, method, seed):
    rng = np.random.default_rng(seed)
    n = 12000
    true_p = rng.beta(1.5, 5, n)
    y = (rng.random(n) < true_p).astype(int)
    score = true_p**0.4                                      # thứ hạng đúng, xác suất sai
    cal, new = slice(0, n // 2), slice(n // 2, n)
    out = nb.recalibrate(score[cal], y[cal], score[new], method=method)
    assert out.shape == (n // 2,)
    assert np.all((out >= 0) & (out <= 1))
    assert nb.expected_calibration_error(y[new], out) < 0.04
    assert np.mean((out - y[new]) ** 2) < np.mean((score[new] - y[new]) ** 2) - 0.05
    order = np.argsort(score[new])
    assert np.all(np.diff(out[order]) >= -1e-12)            # không đảo thứ hạng


def test_real_telco(nb):
    path = ex.dataset("telco-churn") / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
    X, y = nb.load_telco(path)
    assert X.shape == (7043, 19)
    assert "customerID" not in X and "Churn" not in X
    assert y.mean() == pytest.approx(0.2654, abs=1e-4)
    assert X.TotalCharges.dtype.kind == "f" and X.TotalCharges.isna().sum() == 0
    assert (X.TotalCharges == 0).sum() == 11
