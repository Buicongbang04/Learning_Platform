import numpy as np
import pandas as pd
import pytest
from scipy import stats

from testkit import ROOT, Exercise

ex = Exercise(__file__)

# Tổng thể sinh trong test: một tổng thể chuẩn và hai tổng thể lệch phải (lognormal)
NORMAL = np.random.default_rng(100).normal(50, 10, 200_000)
SKEWED = np.random.default_rng(101).lognormal(0, 1.5, 200_000)
MILD = np.random.default_rng(102).lognormal(0, 1.0, 200_000)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("clt.ipynb")


def test_sample_means_shape_and_reproducible(nb):
    m = nb.sample_means(MILD, 25, n_sims=500, seed=3)
    assert m.shape == (500,)
    assert np.array_equal(m, nb.sample_means(MILD, 25, n_sims=500, seed=3))
    assert not np.array_equal(m, nb.sample_means(MILD, 25, n_sims=500, seed=4))


def test_sample_means_center_and_spread(nb):
    m = nb.sample_means(NORMAL, 100, n_sims=4000, seed=0)
    assert m.mean() == pytest.approx(NORMAL.mean(), abs=0.1)
    assert m.std() == pytest.approx(NORMAL.std() / 10, rel=0.05)    # sigma / sqrt(n)


def test_skewness_of_means_shrinks_with_n(nb):
    assert stats.skew(nb.sample_means(MILD, 4, n_sims=4000, seed=0)) > 1.5
    assert stats.skew(nb.sample_means(MILD, 400, n_sims=4000, seed=0)) < 0.5


def test_coverage_nominal_for_normal_population(nb):
    assert 0.935 <= nb.t_interval_coverage(NORMAL, 10, n_sims=4000, seed=0) <= 0.965


def test_coverage_poor_for_skewed_small_n(nb):
    assert nb.t_interval_coverage(SKEWED, 10, n_sims=4000, seed=0) < 0.78


def test_coverage_improves_with_n(nb):
    small = nb.t_interval_coverage(SKEWED, 10, n_sims=2000, seed=1)
    large = nb.t_interval_coverage(SKEWED, 1000, n_sims=2000, seed=1)
    assert large > small + 0.12


def test_coverage_respects_alpha(nb):
    c95 = nb.t_interval_coverage(NORMAL, 20, n_sims=4000, seed=2)
    c80 = nb.t_interval_coverage(NORMAL, 20, n_sims=4000, seed=2, alpha=0.2)
    assert 0.77 <= c80 <= 0.83 and c80 < c95


def test_min_n_for_coverage(nb):
    assert nb.min_n_for_coverage(NORMAL, [30, 5, 10]) == 5          # duyệt theo thứ tự tăng dần
    assert nb.min_n_for_coverage(SKEWED, [10, 30, 100, 300, 1000, 3000]) > 100
    assert nb.min_n_for_coverage(SKEWED, [5, 10], target=0.94) is None


def test_real_olist_order_value(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_order_items_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv")
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    value = (items.assign(v=items.price + items.freight_value).groupby("order_id").v.sum()
             .reindex(delivered.order_id).dropna().to_numpy())
    assert len(value) == 96470
    assert 0.80 <= nb.t_interval_coverage(value, 30, n_sims=4000, seed=0) <= 0.89
    assert nb.t_interval_coverage(value, 2000, n_sims=1000, seed=0) >= 0.92
