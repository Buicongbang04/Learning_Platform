import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def iv():
    return ex.module("intervals.py")


def snaive(train, h):
    return np.asarray(train, float)[-7:][np.arange(h) % 7]


def ar_series(seed, n=2000):
    """Mùa vụ tuần + AR(1) quanh mức 200: sai số dự báo có phân phối ổn định theo thời gian."""
    rng = np.random.default_rng(seed)
    e = np.zeros(n)
    for t in range(1, n):
        e[t] = 0.6 * e[t - 1] + rng.normal(0, 10)
    week = np.tile([20.0, 18, 15, 10, 0, -35, -28], n // 7 + 1)[:n]
    return pd.Series(200 + week + e, index=pd.date_range("2016-01-04", periods=n, freq="D"))


def test_backtest_errors_structure(iv):
    s = pd.Series(np.arange(60.0), index=pd.date_range("2018-01-01", periods=60, freq="D"))
    seen = []

    def spy(train, h):
        seen.append(len(train))
        return np.zeros(h)

    bt = iv.backtest_errors(s, spy, [pd.Timestamp("2018-01-29"), pd.Timestamp("2018-02-05")], 7)
    assert seen == [28, 35]
    assert list(bt.columns) == ["cutoff", "h", "y_true", "y_pred"]
    assert len(bt) == 14 and list(bt.h[:7]) == list(range(1, 8))
    assert list(bt.y_true[:3]) == [28.0, 29.0, 30.0]


def test_empirical_interval_additive_matches_quantiles(iv):
    rng = np.random.default_rng(0)
    bt = pd.DataFrame({"h": np.repeat([1, 2, 3], 50), "y_pred": 100.0})
    bt["y_true"] = 100 + rng.normal(0, 1, 150) * np.repeat([5, 10, 20], 50)
    lo, hi = iv.empirical_interval(np.array([200.0, 210.0, 220.0]), bt, alpha=0.2)
    for k, (point, l, u) in enumerate(zip([200, 210, 220], lo, hi), start=1):
        e = (bt.y_true - bt.y_pred)[bt.h == k]
        assert l == pytest.approx(point + np.quantile(e, 0.1))
        assert u == pytest.approx(point + np.quantile(e, 0.9))
    assert hi[2] - lo[2] > hi[0] - lo[0]       # bước xa hơn → khoảng rộng hơn


def test_empirical_interval_log_ratio(iv):
    bt = pd.DataFrame({"h": [1] * 5, "y_pred": [100.0] * 5, "y_true": [80.0, 90.0, 100.0, 110.0, 125.0]})
    lo, hi = iv.empirical_interval(np.array([300.0]), bt, alpha=0.5, kind="log_ratio")
    r = np.log(bt.y_true / bt.y_pred)
    assert lo[0] == pytest.approx(300 * np.exp(np.quantile(r, 0.25)))
    assert hi[0] == pytest.approx(300 * np.exp(np.quantile(r, 0.75)))


def test_empirical_interval_errors(iv):
    bt = pd.DataFrame({"h": [1, 1], "y_pred": [1.0, 1.0], "y_true": [1.0, 2.0]})
    with pytest.raises(ValueError):
        iv.empirical_interval(np.array([5.0, 5.0]), bt)          # thiếu h = 2
    with pytest.raises(ValueError):
        iv.empirical_interval(np.array([5.0]), bt, kind="magic")


def test_coverage(iv):
    assert iv.coverage([1, 5, 10, 3], [0, 5, 0, 4], [2, 6, 9, 9]) == pytest.approx(0.5)


def test_interval_score(iv):
    # trong khoảng: chỉ độ rộng; dưới lo: + 2/alpha * (lo - y); trên hi: + 2/alpha * (y - hi)
    s = iv.interval_score([5.0, 0.0, 12.0], [2.0, 2.0, 2.0], [8.0, 8.0, 8.0], alpha=0.2)
    assert s == pytest.approx((6 + (6 + 10 * 2) + (6 + 10 * 4)) / 3)


def test_pinball_loss(iv):
    assert iv.pinball_loss([10.0], [8.0], 0.9) == pytest.approx(0.9 * 2)
    assert iv.pinball_loss([10.0], [12.0], 0.9) == pytest.approx(0.1 * 2)


def test_pinball_is_minimised_by_the_true_quantile(iv):
    y = np.random.default_rng(1).normal(0, 1, 20000)
    grid = np.linspace(-2, 3, 101)
    best = grid[np.argmin([iv.pinball_loss(y, np.full_like(y, g), 0.9) for g in grid])]
    assert best == pytest.approx(norm.ppf(0.9), abs=0.06)


@pytest.mark.parametrize("seed", range(5))
def test_empirical_interval_is_calibrated_on_stable_series(iv, seed):
    # Bản tham chiếu, 30 seed: coverage 80% danh nghĩa nằm trong [0.72, 0.84]
    s = ar_series(seed)
    calib = s.index[300:1000:3]
    evaluate = s.index[1020:1980:7]
    bt = iv.backtest_errors(s, snaive, calib, 14)
    ev = iv.backtest_errors(s, snaive, evaluate, 14)
    lo, hi = [], []
    for c in evaluate:
        point = ev[ev.cutoff == c].y_pred.to_numpy()
        l, u = iv.empirical_interval(point, bt, alpha=0.2)
        lo.append(l)
        hi.append(u)
    cov = iv.coverage(ev.y_true, np.concatenate(lo), np.concatenate(hi))
    assert 0.70 <= cov <= 0.90


def test_real_olist(iv):
    path = ROOT / "data" / "raw" / "olist_orders_dataset.csv"
    if not path.exists():
        pytest.skip("Chưa có Olist thật. Chạy: uv run python data/download_olist.py")
    ts = pd.to_datetime(pd.read_csv(path, usecols=["order_purchase_timestamp"]).order_purchase_timestamp)
    y = ts.dt.normalize().value_counts().reindex(pd.date_range("2017-01-09", "2018-08-19"), fill_value=0).astype(float)
    calib = pd.date_range("2017-06-04", "2018-02-18", freq="7D")
    evaluate = pd.date_range("2018-03-04", periods=12, freq="14D")
    bt = iv.backtest_errors(y, snaive, calib, 14)
    ev = iv.backtest_errors(y, snaive, evaluate, 14)
    lo, hi = [], []
    for c in evaluate:
        l, u = iv.empirical_interval(ev[ev.cutoff == c].y_pred.to_numpy(), bt, alpha=0.2)
        lo.append(l)
        hi.append(u)
    lo, hi = np.concatenate(lo), np.concatenate(hi)
    # 2018 cao hơn giai đoạn hiệu chỉnh nên sai số tuyệt đối lớn hơn: khoảng additive phủ thiếu
    assert iv.coverage(ev.y_true, lo, hi) == pytest.approx(0.685, abs=0.005)
    assert iv.interval_score(ev.y_true, lo, hi, 0.2) == pytest.approx(214.5, abs=0.5)


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300
