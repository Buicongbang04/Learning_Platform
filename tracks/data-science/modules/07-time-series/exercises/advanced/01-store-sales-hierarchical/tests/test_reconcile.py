import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

MAPPING = pd.Series(["b", "a", "b", "a", "a"], index=[11, 12, 13, 14, 15])
NODES = ["Total", "a", "b", 11, 12, 13, 14, 15]
METHODS = ["bottom_up", "ols", "wls_struct", "wls_var"]


@pytest.fixture(scope="module")
def rc():
    return ex.module("reconcile.py")


def truth(seed, n=8):
    rng = np.random.default_rng(seed)
    bottom = pd.DataFrame(rng.gamma(5, 100, (n, 5)), columns=MAPPING.index)
    return bottom


def noisy_base(rc, seed):
    S = rc.summing_matrix(MAPPING)
    y = rc.aggregate(truth(seed), S)
    rng = np.random.default_rng(seed + 100)
    sd = np.array([400, 200, 200, 60, 60, 60, 60, 60.0])
    return S, y, y + rng.normal(0, 1, y.shape) * sd


def residuals(seed):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(0, 1, (40, 8)) * [400, 200, 200, 60, 60, 60, 60, 60.0], columns=NODES)


def test_summing_matrix(rc):
    S = rc.summing_matrix(MAPPING)
    assert list(S.index) == NODES and list(S.columns) == [11, 12, 13, 14, 15]
    np.testing.assert_array_equal(S.loc["Total"], [1, 1, 1, 1, 1])
    np.testing.assert_array_equal(S.loc["a"], [0, 1, 0, 1, 1])
    np.testing.assert_array_equal(S.loc["b"], [1, 0, 1, 0, 0])
    np.testing.assert_array_equal(S.loc[[11, 12, 13, 14, 15]].to_numpy(), np.eye(5))


def test_aggregate(rc):
    S = rc.summing_matrix(MAPPING)
    bottom = truth(0)
    y = rc.aggregate(bottom, S)
    assert list(y.columns) == NODES
    np.testing.assert_allclose(y.Total, bottom.sum(axis=1))
    np.testing.assert_allclose(y.a, bottom[[12, 14, 15]].sum(axis=1))


def test_is_coherent(rc):
    S, y, base = noisy_base(rc, 1)
    assert rc.is_coherent(y, S)
    assert not rc.is_coherent(base, S)


@pytest.mark.parametrize("method", METHODS)
def test_every_method_is_coherent(rc, method):
    S, _, base = noisy_base(rc, 2)
    out = rc.reconcile(base, S, method, residuals=residuals(2))
    assert list(out.columns) == NODES and out.index.equals(base.index)
    assert rc.is_coherent(out, S)


def test_bottom_up_keeps_store_forecasts(rc):
    S, _, base = noisy_base(rc, 3)
    out = rc.reconcile(base, S, "bottom_up")
    stores = [11, 12, 13, 14, 15]
    pd.testing.assert_frame_equal(out[stores], base[stores], check_dtype=False)


@pytest.mark.parametrize("method", ["ols", "wls_struct", "wls_var"])
def test_coherent_forecasts_are_unchanged(rc, method):
    S, y, _ = noisy_base(rc, 4)
    out = rc.reconcile(y, S, method, residuals=residuals(4))
    np.testing.assert_allclose(out.to_numpy(), y.to_numpy(), rtol=1e-9)


def test_ols_formula(rc):
    S, _, base = noisy_base(rc, 5)
    Sm = S.to_numpy(float)
    expected = base.to_numpy() @ (Sm @ np.linalg.solve(Sm.T @ Sm, Sm.T)).T
    np.testing.assert_allclose(rc.reconcile(base, S, "ols").to_numpy(), expected, rtol=1e-9)


def test_wls_struct_formula(rc):
    S, _, base = noisy_base(rc, 6)
    Sm = S.to_numpy(float)
    Winv = np.diag(1 / Sm.sum(axis=1))      # Total: 5, a: 3, b: 2, cửa hàng: 1
    expected = base.to_numpy() @ (Sm @ np.linalg.solve(Sm.T @ Winv @ Sm, Sm.T @ Winv)).T
    np.testing.assert_allclose(rc.reconcile(base, S, "wls_struct").to_numpy(), expected, rtol=1e-9)


def test_wls_var_uses_residual_variance(rc):
    S, _, base = noisy_base(rc, 7)
    res = residuals(7)
    Sm = S.to_numpy(float)
    Winv = np.diag(1 / res[NODES].var(ddof=1).to_numpy())
    expected = base.to_numpy() @ (Sm @ np.linalg.solve(Sm.T @ Winv @ Sm, Sm.T @ Winv)).T
    np.testing.assert_allclose(rc.reconcile(base, S, "wls_var", residuals=res).to_numpy(), expected, rtol=1e-9)


def test_bad_arguments(rc):
    S, _, base = noisy_base(rc, 8)
    with pytest.raises(ValueError):
        rc.reconcile(base, S, "wls_var")
    with pytest.raises(ValueError):
        rc.reconcile(base, S, "magic")


@pytest.mark.parametrize("seed", range(10))
def test_ols_never_increases_total_squared_error(rc, seed):
    # Phép chiếu trực giao lên không gian coherent (chứa giá trị thật) luôn rút ngắn khoảng cách tới giá trị thật
    S, y, base = noisy_base(rc, seed)
    out = rc.reconcile(base, S, "ols")
    assert ((out - y) ** 2).to_numpy().sum() <= ((base - y) ** 2).to_numpy().sum() + 1e-6


def test_real_rossmann(rc):
    root = ex.dataset("store-sales")
    train = pd.read_csv(root / "train.csv", dtype={"StateHoliday": str}, parse_dates=["Date"])
    store = pd.read_csv(root / "store.csv")
    bottom, mapping = rc.build_hierarchy(train, store)
    assert bottom.shape == (133, 20)
    assert bottom.index[0] == pd.Timestamp("2013-01-13") and bottom.index[-1] == pd.Timestamp("2015-07-26")
    assert list(mapping.index) == [1, 2, 3, 4, 5, 6, 7, 15, 18, 21, 23, 25, 26, 29, 34, 85, 259, 262, 274, 335]
    assert mapping.value_counts().to_dict() == {"a": 5, "b": 5, "c": 5, "d": 5}
    y = rc.aggregate(bottom, rc.summing_matrix(mapping))
    assert y.Total.sum() == pytest.approx(131_986_711)
    assert y.Total.iloc[-1] == pytest.approx(893_630)


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300
