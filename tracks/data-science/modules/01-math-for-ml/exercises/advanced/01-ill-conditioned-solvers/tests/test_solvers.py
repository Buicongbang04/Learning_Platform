import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def sv():
    return ex.module("solvers.py")


def well_conditioned(n: int = 300, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=(n, 3))])
    return X, X @ rng.normal(size=4) + rng.normal(0, 0.1, n)


def test_polynomial_features(sv):
    out = sv.polynomial_features(np.array([1.0, 2.0, 3.0]), 3)
    assert out == pytest.approx(np.array([[1, 1, 1, 1], [1, 2, 4, 8], [1, 3, 9, 27]], dtype=float))


@pytest.mark.parametrize("seed", [0, 1])
def test_all_solvers_agree_when_well_conditioned(sv, seed):
    X, y = well_conditioned(seed=seed)
    ref, *_ = np.linalg.lstsq(X, y, rcond=None)
    for solve in (sv.solve_normal, sv.solve_qr, sv.solve_svd):
        assert solve(X, y) == pytest.approx(ref, rel=1e-8)


@pytest.mark.parametrize("seed", range(10))
def test_qr_beats_normal_equation_when_ill_conditioned(sv, seed):
    # Vandermonde bậc 10 trên [0, 1]: cond(X) ≈ 2e7, nên cond(XᵀX) ≈ 5e14
    X = sv.polynomial_features(np.linspace(0, 1, 200), 10)
    w = np.random.default_rng(seed).normal(size=11)
    y = X @ w                                           # hệ tương thích: nghiệm đúng là w
    err = lambda v: np.linalg.norm(v - w) / np.linalg.norm(w)
    e_normal, e_qr, e_svd = err(sv.solve_normal(X, y)), err(sv.solve_qr(X, y)), err(sv.solve_svd(X, y, rcond=1e-15))
    assert e_qr < 1e-7 and e_svd < 1e-7
    assert e_normal > 1e3 * e_qr                       # mất khoảng gấp đôi số chữ số đúng


def test_svd_gives_min_norm_solution_when_rank_deficient(sv):
    X, y = well_conditioned(seed=2)
    X = np.column_stack([X, 2 * X[:, 1]])              # cột cuối = 2 × cột 1: XᵀX suy biến
    w = sv.solve_svd(X, y)
    assert np.all(np.isfinite(w))
    assert w == pytest.approx(np.linalg.pinv(X) @ y, rel=1e-8)


@pytest.mark.parametrize("seed", range(10))
def test_svd_rcond_truncates(sv, seed):
    x = np.linspace(0, 1, 200)
    X = sv.polynomial_features(x, 10)
    y = np.sin(6 * x) + 0.01 * np.random.default_rng(seed).normal(size=200)
    w_full = sv.solve_svd(X, y, rcond=1e-15)
    w_trunc = sv.solve_svd(X, y, rcond=1e-6)
    mse = lambda w: np.mean((X @ w - y) ** 2)
    assert np.linalg.norm(w_trunc) < 0.25 * np.linalg.norm(w_full)   # bỏ hướng σ nhỏ: hệ số nhỏ đi nhiều
    assert mse(w_trunc) < 1.05 * mse(w_full)                         # mà gần như không mất độ khớp


@pytest.mark.parametrize("lam", [0.1, 10.0, 1000.0])
def test_ridge_matches_sklearn_with_unpenalized_intercept(sv, lam):
    X, y = well_conditioned(seed=3)
    w = sv.ridge(X, y, lam)
    ref = Ridge(alpha=lam).fit(X[:, 1:], y)
    assert w[0] == pytest.approx(ref.intercept_, rel=1e-8)
    assert w[1:] == pytest.approx(ref.coef_, rel=1e-8)


def test_ridge_shrinks(sv):
    X, y = well_conditioned(seed=4)
    assert sv.ridge(X, y, 0.0) == pytest.approx(np.linalg.lstsq(X, y, rcond=None)[0], rel=1e-8)
    norms = [np.linalg.norm(sv.ridge(X, y, lam)[1:]) for lam in (0.0, 1.0, 100.0, 1e4)]
    assert all(a > b for a, b in zip(norms, norms[1:]))


def test_scaled_condition_number_separates_units_from_collinearity(sv):
    rng = np.random.default_rng(5)
    n = 500
    kg = rng.lognormal(0, 1, n)
    X_units = np.column_stack([np.ones(n), 1000 * kg, 1e6 * rng.lognormal(0, 1, n)])     # g và cm³: chỉ do đơn vị
    assert sv.scaled_condition_number(X_units) < 1e-3 * np.linalg.cond(X_units)
    X_collinear = np.column_stack([np.ones(n), kg, kg + 1e-6 * rng.normal(size=n)])       # gần trùng cột: thật sự xấu
    assert sv.scaled_condition_number(X_collinear) > 1e5


def test_real_olist_volumetric_weight(sv):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_order_items_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    products = pd.read_csv(raw / "olist_products_dataset.csv")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp"])
    df = items.merge(products, on="product_id").merge(orders[["order_id", "order_purchase_timestamp"]], on="order_id")
    df = df.dropna(subset=["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"])
    df = df[df.order_purchase_timestamp < "2018-01-01"]
    volume_cm3 = df.product_length_cm * df.product_height_cm * df.product_width_cm
    # "peso cubado" của bưu điện Brazil: dài × rộng × cao (cm) / 6000, tính bằng kg; = volume_l / 6
    X = np.column_stack([np.ones(len(df)), df.product_weight_g / 1000, volume_cm3 / 1000, volume_cm3 / 6000])
    y = df.freight_value.to_numpy()
    assert sv.scaled_condition_number(X) > 1e8
    w = sv.solve_svd(X, y)
    assert w[1] == pytest.approx(1.4592, abs=5e-4)
    assert w[2] + w[3] / 6 == pytest.approx(0.1790, abs=5e-4)           # hai cột trùng nhau chia nhau hệ số
    assert w[3] == pytest.approx(w[2] / 6, rel=1e-6)                   # nghiệm min-norm: chia theo tỉ lệ cột
