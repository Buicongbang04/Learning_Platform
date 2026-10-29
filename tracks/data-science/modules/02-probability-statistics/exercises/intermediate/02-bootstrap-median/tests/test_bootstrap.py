import numpy as np
import pandas as pd
import pytest
from scipy import stats

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("bootstrap.ipynb")


def test_bootstrap_stats_shape_and_reproducible(nb):
    x = np.random.default_rng(0).lognormal(2.3, 0.7, 300)
    b = nb.bootstrap_stats(x, np.median, n_boot=700, seed=4)
    assert b.shape == (700,)
    assert np.array_equal(b, nb.bootstrap_stats(x, np.median, n_boot=700, seed=4))
    assert b.min() >= x.min() and b.max() <= x.max()


def test_bootstrap_of_mean_has_standard_error_spread(nb):
    x = np.random.default_rng(1).normal(10, 3, 400)
    b = nb.bootstrap_stats(x, np.mean, n_boot=4000, seed=0)
    assert b.std() == pytest.approx(x.std() / np.sqrt(len(x)), rel=0.06)


def test_bootstrap_stats_handles_large_input(nb):
    # 100 nghìn × 2000 không vừa một ma trận hợp lý: phải chia lô
    x = np.random.default_rng(2).exponential(10, 100_000)
    b = nb.bootstrap_stats(x, np.median, n_boot=2000, seed=0)
    assert b.shape == (2000,)
    assert np.median(x) == pytest.approx(b.mean(), rel=0.01)


def test_percentile_ci_basic_properties(nb):
    x = np.random.default_rng(3).lognormal(2.3, 0.7, 150)
    lo, hi = nb.percentile_ci(x)
    assert lo < np.median(x) < hi
    lo90, hi90 = nb.percentile_ci(x, alpha=0.1)
    assert lo <= lo90 and hi90 <= hi
    assert nb.percentile_ci(x, seed=9) == nb.percentile_ci(x, seed=9)


def test_percentile_ci_matches_quantiles_of_bootstrap(nb):
    x = np.random.default_rng(4).gamma(2.0, 5.0, 120)
    boot = nb.bootstrap_stats(x, np.median, 1000, 5)
    assert nb.percentile_ci(x, np.median, 1000, 5) == pytest.approx(tuple(np.quantile(boot, [0.025, 0.975])))


@pytest.mark.parametrize("n, alpha", [(41, 0.05), (200, 0.05), (1000, 0.01), (10, 0.05)])
def test_median_ci_exact_order_statistics(nb, n, alpha):
    x = np.random.default_rng(n).lognormal(3, 0.6, n)
    xs = np.sort(x)
    j = max(int(stats.binom.ppf(alpha / 2, n, 0.5)), 1)
    assert nb.median_ci_exact(x, alpha) == pytest.approx((xs[j - 1], xs[n - j]))


def test_coverage_of_both_intervals(nb):
    # median thật của Lognormal(2.3, 0.7) là e^2.3; 200 lần lặp, mỗi lần 200 quan sát
    rng = np.random.default_rng(1000)
    true = np.exp(2.3)
    boot_hits = exact_hits = 0
    for r in range(200):
        y = rng.lognormal(2.3, 0.7, 200)
        lo, hi = nb.percentile_ci(y, n_boot=1000, seed=r)
        boot_hits += lo <= true <= hi
        lo, hi = nb.median_ci_exact(y)
        exact_hits += lo <= true <= hi
    assert 0.89 <= boot_hits / 200 <= 0.99
    assert exact_hits / 200 >= 0.91


def make_df():
    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "state": ["A"] * 300 + ["B"] * 40 + ["C"] * 5,
        "days": np.concatenate([rng.lognormal(2.0, 0.5, 300), rng.lognormal(3.0, 0.5, 40), [5, 6, 7, 8, 9.0]]),
    })


def test_ci_table_structure(nb):
    df = make_df()
    table = nb.ci_table(df, "days", "state", n_boot=500)
    assert list(table.columns) == ["n", "median", "boot_lo", "boot_hi", "exact_lo", "exact_hi"]
    assert list(table.index) == ["B", "A", "C"]                 # median giảm dần
    assert table.loc["A", "n"] == 300 and table.loc["C", "n"] == 5
    assert table.loc["C", "median"] == pytest.approx(7.0)
    assert (table.boot_lo <= table["median"]).all() and (table["median"] <= table.boot_hi).all()


def test_ci_table_uses_same_seed_per_group(nb):
    df = make_df()
    table = nb.ci_table(df, "days", "state", n_boot=500, seed=3)
    b = df.loc[df.state == "B", "days"].to_numpy()
    assert (table.loc["B", "boot_lo"], table.loc["B", "boot_hi"]) == pytest.approx(nb.percentile_ci(b, np.median, 500, 3))


def test_ci_table_min_n(nb):
    table = nb.ci_table(make_df(), "days", "state", min_n=30, n_boot=200)
    assert set(table.index) == {"A", "B"}


def test_real_olist_delivery_days_rr(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_customers_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    customers = pd.read_csv(raw / "olist_customers_dataset.csv")
    df = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    df = df.merge(customers[["customer_id", "customer_state"]], on="customer_id")
    df["days"] = (df.order_delivered_customer_date - df.order_purchase_timestamp).dt.total_seconds() / 86400
    rr = nb.ci_table(df[df.customer_state.isin(["RR", "SP"])], "days", "customer_state")
    assert rr.loc["RR", "n"] == 41 and rr.loc["SP", "n"] == 40494
    assert rr.loc["RR", "median"] == pytest.approx(25.01, abs=0.01)
    assert (rr.loc["RR", "exact_lo"], rr.loc["RR", "exact_hi"]) == pytest.approx((17.04, 30.19), abs=0.01)
    assert rr.loc["RR", "boot_hi"] - rr.loc["RR", "boot_lo"] > 10 > 1 > rr.loc["SP", "boot_hi"] - rr.loc["SP", "boot_lo"]
