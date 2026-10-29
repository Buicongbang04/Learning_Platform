import numpy as np
import pandas as pd
import pytest
from scipy.stats import ks_2samp

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def drift():
    return ex.module("drift.py")


def test_psi_identical_is_zero(drift):
    x = np.random.default_rng(0).normal(size=5000)
    assert drift.psi(x, x) == pytest.approx(0.0, abs=1e-12)


def test_psi_hand_computed(drift):
    # 4 bin theo quantile của expected: mỗi bin 25%. actual 50..149 rơi vào 0%, 0%, 25%, 75%.
    expected = np.arange(100)
    actual = np.arange(50, 150)
    want = 2 * (1e-4 - 0.25) * np.log(1e-4 / 0.25) + 0.5 * np.log(3)
    assert drift.psi(expected, actual, bins=4) == pytest.approx(want, rel=1e-6)


def test_psi_is_not_symmetric(drift):
    rng = np.random.default_rng(1)
    a, b = rng.normal(size=4000), rng.normal(1.0, 2.0, size=4000)
    assert drift.psi(a, b) != pytest.approx(drift.psi(b, a), rel=0.01)


def test_psi_grows_with_shift(drift):
    rng = np.random.default_rng(2)
    ref = rng.normal(size=20000)
    values = [drift.psi(ref, rng.normal(shift, 1, 20000)) for shift in (0.0, 0.2, 0.5, 1.0)]
    assert values == sorted(values)
    assert values[0] < 0.01 and values[-1] > 0.25


def test_psi_values_outside_reference_range_are_counted(drift):
    ref = np.linspace(0, 1, 1000)
    far = np.full(1000, 5.0)          # toàn bộ nằm ngoài khoảng của reference
    assert drift.psi(ref, far) > 1.0


def test_psi_ignores_nan(drift):
    rng = np.random.default_rng(3)
    x = rng.normal(size=3000)
    with_nan = np.concatenate([x, [np.nan] * 50])
    assert drift.psi(with_nan, x) == pytest.approx(0.0, abs=1e-12)
    assert drift.psi(pd.Series(with_nan), pd.Series(with_nan)) == pytest.approx(0.0, abs=1e-12)


def test_psi_heavy_ties_does_not_crash(drift):
    # như n_items của Olist: gần như toàn bộ bằng 1
    rng = np.random.default_rng(4)
    a = np.where(rng.random(5000) < 0.9, 1, rng.integers(2, 5, 5000))
    b = np.where(rng.random(5000) < 0.9, 1, rng.integers(2, 5, 5000))
    value = drift.psi(a, b)
    assert np.isfinite(value) and value < 0.05
    assert drift.psi(np.ones(100), np.ones(100)) == pytest.approx(0.0, abs=1e-12)


def test_psi_categorical(drift):
    ref = pd.Series(["SP"] * 60 + ["RJ"] * 30 + ["MG"] * 10)
    assert drift.psi_categorical(ref, ref.sample(frac=1, random_state=0)) == pytest.approx(0.0, abs=1e-12)
    cur = pd.Series(["SP"] * 50 + ["RJ"] * 30 + ["MG"] * 10 + ["BA"] * 10)   # BA chưa từng thấy
    want = (0.5 - 0.6) * np.log(0.5 / 0.6) + (0.1 - 1e-4) * np.log(0.1 / 1e-4)
    assert drift.psi_categorical(ref, cur) == pytest.approx(want, rel=1e-6)


def test_psi_categorical_counts_missing_as_category(drift):
    ref = pd.Series(["a"] * 90 + ["b"] * 10)
    cur = pd.Series(["a"] * 70 + ["b"] * 10 + [None] * 20)
    assert drift.psi_categorical(ref, cur) > 0.5


def test_ks_statistic_matches_scipy(drift):
    rng = np.random.default_rng(5)
    for n, m in [(500, 700), (3000, 1000)]:
        a, b = rng.normal(size=n), rng.normal(0.2, 1.3, size=m)
        assert drift.ks_statistic(a, b) == pytest.approx(ks_2samp(a, b).statistic, abs=1e-12)
    ties_a = rng.integers(0, 5, 800)
    ties_b = rng.integers(0, 6, 900)
    assert drift.ks_statistic(ties_a, ties_b) == pytest.approx(ks_2samp(ties_a, ties_b).statistic, abs=1e-12)


def test_drift_level_boundaries(drift):
    assert drift.drift_level(0.0) == "stable"
    assert drift.drift_level(0.0999) == "stable"
    assert drift.drift_level(0.1) == "moderate"
    assert drift.drift_level(0.2499) == "moderate"
    assert drift.drift_level(0.25) == "major"


def test_big_sample_tiny_shift_ks_significant_but_psi_stable(drift):
    # Với mẫu lớn, KS p-value gần như luôn "có ý nghĩa"; PSI đo độ lớn nên vẫn "stable".
    rng = np.random.default_rng(6)
    a, b = rng.normal(size=200_000), rng.normal(0.03, 1, size=200_000)
    assert ks_2samp(a, b).pvalue < 0.001
    assert drift.drift_level(drift.psi(a, b)) == "stable"
    assert drift.ks_statistic(a, b) < 0.03


def test_real_olist_delay_days():
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    drift = ex.module("drift.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    latest = reviews.sort_values("review_answer_timestamp", kind="stable").drop_duplicates("order_id", keep="last")
    df = delivered.merge(latest[["order_id", "review_score"]], on="order_id")
    df["delay_days"] = (df.order_delivered_customer_date - df.order_estimated_delivery_date) / pd.Timedelta(days=1)
    t = df.order_purchase_timestamp
    train = df[t < "2018-01-01"].delay_days
    test = df[(t >= "2018-04-01") & (t < "2018-09-01")].delay_days
    assert drift.psi(train, test) == pytest.approx(0.0729, abs=0.002)
    assert drift.ks_statistic(train, test) == pytest.approx(0.0785, abs=0.001)
    assert drift.drift_level(drift.psi(train, test)) == "stable"
