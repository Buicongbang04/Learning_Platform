import numpy as np
import pytest
import statsmodels.api as sm

from testkit import Exercise

ex = Exercise(__file__)

TAU = 0.3


@pytest.fixture(scope="module")
def rdd():
    return ex.module("rdd.py")


def simulate(n: int = 20000, seed: int = 0, bunching: bool = False):
    """Điểm x trong [-1, 1], ngưỡng 0. Bên phải đường cong (không tuyến tính), bước nhảy thật là TAU."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1, 1, n)
    if bunching:
        # 30% người ở ngay dưới ngưỡng "đẩy" được điểm của mình lên ngay trên ngưỡng
        near = (x > -0.05) & (x < 0) & (rng.random(n) < 0.3)
        x[near] = -x[near]
    f = np.where(x >= 0, 0.5 + x + 2.0 * x**2, 0.5 + x)
    y = f + TAU * (x >= 0) + rng.normal(0, 0.5, n)
    return x, y


def test_matches_statsmodels_wls(rdd):
    x, y = simulate(n=3000, seed=11)
    r = x - 0.1
    keep = np.abs(r) < 0.4
    rk, yk = r[keep], y[keep]
    d = (rk >= 0).astype(float)
    X = np.column_stack([np.ones_like(rk), d, rk, d * rk])
    ref = sm.WLS(yk, X, weights=1 - np.abs(rk) / 0.4).fit(cov_type="HC1")
    est, se = rdd.rdd_estimate(x, y, cutoff=0.1, bandwidth=0.4)
    assert est == pytest.approx(ref.params[1], abs=1e-8)
    assert se == pytest.approx(ref.bse[1], abs=1e-8)


@pytest.mark.parametrize("seed", range(5))
def test_recovers_jump_with_small_bandwidth(rdd, seed):
    x, y = simulate(seed=seed)
    est, se = rdd.rdd_estimate(x, y, cutoff=0.0, bandwidth=0.2)
    assert est == pytest.approx(TAU, abs=4 * se)
    assert abs(est - TAU) < 0.12


@pytest.mark.parametrize("seed", range(5))
def test_wide_bandwidth_is_biased_by_curvature(rdd, seed):
    x, y = simulate(seed=seed)
    est, _ = rdd.rdd_estimate(x, y, cutoff=0.0, bandwidth=1.0)
    assert est < TAU - 0.1        # đường cong bên phải bị tuyến tính hoá → bước nhảy bị kéo xuống


def test_bandwidth_sensitivity_table(rdd):
    x, y = simulate(seed=3)
    table = rdd.bandwidth_sensitivity(x, y, 0.0, [0.1, 0.2, 0.5])
    assert list(table.columns) == ["bandwidth", "estimate", "se", "n"]
    assert list(table.bandwidth) == [0.1, 0.2, 0.5]
    assert table.n.is_monotonic_increasing
    assert table.se.iloc[0] > table.se.iloc[-1]       # bandwidth hẹp: ít dữ liệu, SE lớn
    est, _ = rdd.rdd_estimate(x, y, 0.0, 0.2)
    assert table.estimate.iloc[1] == pytest.approx(est)


def test_density_check(rdd):
    x = np.array([-0.3, -0.2, -0.1, 0.1, 0.2, 0.3, 0.4, 0.5])
    assert rdd.density_check(x, 0.0, 0.35) == pytest.approx(1.0)       # 3 trái, 3 phải
    assert rdd.density_check(x, 0.0, 1.0) == pytest.approx(0.7265625)  # 3 trái, 5 phải


@pytest.mark.parametrize("seed", range(5))
def test_density_check_detects_bunching(rdd, seed):
    clean, _ = simulate(seed=seed)
    gamed, _ = simulate(seed=seed, bunching=True)
    assert rdd.density_check(clean, 0.0, 0.05) > 0.001
    assert rdd.density_check(gamed, 0.0, 0.05) < 0.001
