import math

import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)
RAW = ROOT / "data" / "raw"
KEYS = {"n", "n_missing", "mean", "median", "std", "skew", "p01", "p99", "zero_share", "tail_ratio"}


@pytest.fixture(scope="module")
def dist():
    return ex.module("distribution.py")


def test_shape_summary_small(dist):
    s = pd.Series([0.0, 1, 2, 3, 4, np.nan])
    out = dist.shape_summary(s)
    assert set(out) == KEYS
    assert out["n"] == 5 and out["n_missing"] == 1
    assert out["mean"] == pytest.approx(2.0)
    assert out["median"] == pytest.approx(2.0)
    assert out["std"] == pytest.approx(np.std([0, 1, 2, 3, 4], ddof=1))
    assert out["skew"] == pytest.approx(0.0, abs=1e-12)
    assert out["p99"] == pytest.approx(3.96)
    assert out["p01"] == pytest.approx(0.04)
    assert out["zero_share"] == pytest.approx(0.2)
    assert out["tail_ratio"] == pytest.approx(3.96 / 2.0)


def test_tail_ratio_undefined_when_median_not_positive(dist):
    out = dist.shape_summary(pd.Series([0, 0, 0, 5, 9]))
    assert math.isnan(out["tail_ratio"])


def test_skew_sign(dist):
    rng = np.random.default_rng(1)
    assert dist.shape_summary(pd.Series(rng.lognormal(0, 1, 5000)))["skew"] > 2
    assert dist.shape_summary(pd.Series(-rng.lognormal(0, 1, 5000)))["skew"] < -2


def test_suggest_scale_rules(dist):
    rng = np.random.default_rng(2)
    heavy = pd.Series(rng.lognormal(3, 1.5, 20000))           # p99/median ≈ e^(2.33·1.5) ≈ 33
    assert dist.suggest_scale(heavy) == "log"
    with_zero = heavy.copy()
    with_zero.iloc[:50] = 0.0
    assert dist.suggest_scale(with_zero) == "log1p"
    light = pd.Series(rng.normal(100, 10, 20000))
    assert dist.suggest_scale(light) == "linear"
    negative = heavy - 1.0
    negative.iloc[0] = -5.0
    assert dist.suggest_scale(negative) == "linear"
    assert dist.suggest_scale(pd.Series([0, 0, 0, 0, 7.0])) == "linear"      # median 0


def test_suggest_scale_threshold(dist):
    s = pd.Series(np.r_[np.ones(980), np.full(20, 6.0)])      # p99 = 6, median = 1
    assert dist.suggest_scale(s) == "linear"
    assert dist.suggest_scale(s, tail_threshold=5) == "log"


def test_fd_bins_matches_numpy(dist):
    rng = np.random.default_rng(3)
    for x in [rng.normal(size=1000), rng.lognormal(size=5000), rng.uniform(0, 7, 333)]:
        expected = len(np.histogram_bin_edges(x, bins="fd")) - 1
        assert dist.fd_bins(pd.Series(x)) == expected


def test_fd_bins_ignores_nan_and_degenerate_iqr(dist):
    x = pd.Series([1.0, 2, 3, 4, 5, 6, 7, 8, np.nan])
    assert dist.fd_bins(x) == len(np.histogram_bin_edges(x.dropna(), bins="fd")) - 1
    # 90% giá trị bằng nhau → IQR = 0 → Sturges: ceil(log2(100)) + 1 = 8
    assert dist.fd_bins(pd.Series([5.0] * 90 + list(range(10)))) == 8


def test_ecdf(dist):
    out = dist.ecdf(pd.Series([3.0, 1.0, np.nan, 2.0, 2.0]))
    assert list(out.columns) == ["x", "y"]
    assert out["x"].tolist() == [1.0, 2.0, 2.0, 3.0]
    assert out["y"].tolist() == pytest.approx([0.25, 0.5, 0.75, 1.0])


def _real(name):
    path = RAW / name
    if not path.exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    return pd.read_csv(path)


def test_real_olist_items(dist):
    items = _real("olist_order_items_dataset.csv")
    out = dist.shape_summary(items.price)
    assert out["median"] == pytest.approx(74.99)
    assert out["p99"] == pytest.approx(890.0)
    assert out["tail_ratio"] == pytest.approx(11.87, abs=0.01)
    assert dist.suggest_scale(items.price) == "log"
    assert dist.suggest_scale(items.freight_value) == "linear"     # p99/median ≈ 5.2
    assert dist.fd_bins(items.price) == 1712


def test_real_olist_payments(dist):
    payments = _real("olist_order_payments_dataset.csv")
    assert dist.suggest_scale(payments.payment_value) == "log1p"   # 9 thanh toán bằng 0
