import warnings

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.statespace.sarimax import SARIMAX

from testkit import ROOT, Exercise

ex = Exercise(__file__)

CUTOFFS = pd.date_range("2018-03-04", periods=12, freq="14D")


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("sarima.ipynb")


def weekly_trend_series(seed, n=280):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    week = np.tile([20.0, 18, 15, 10, 0, -35, -28], n // 7 + 1)[:n]
    return 100 + 0.3 * t + week + rng.normal(0, 6, n)


ORDERS = pd.DataFrame({"order_purchase_timestamp": [
    "2018-01-01 09:00:00", "2018-01-01 23:59:59", "2018-01-03 00:00:00",
    "2017-12-31 23:00:00", "2018-01-05 10:00:00", "2018-01-05 11:00:00", "2018-01-05 12:00:00",
]})


def test_daily_orders_fills_missing_days(nb):
    s = nb.daily_orders(ORDERS, start="2018-01-01", end="2018-01-06")
    assert list(s.index) == list(pd.date_range("2018-01-01", "2018-01-06"))
    assert list(s) == [2, 0, 1, 0, 3, 0]
    assert s.dtype == float


def test_seasonal_naive(nb):
    out = nb.seasonal_naive(np.arange(1.0, 15.0), 9)
    np.testing.assert_allclose(out, [8, 9, 10, 11, 12, 13, 14, 8, 9])


def test_sarima_forecast_is_the_prescribed_model(nb):
    y = weekly_trend_series(0, 200)
    out = nb.sarima_forecast(y, 10)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ref = SARIMAX(y, order=(1, 1, 1), seasonal_order=(0, 1, 1, 7)).fit(disp=False).forecast(10)
    assert isinstance(out, np.ndarray) and out.shape == (10,)
    np.testing.assert_allclose(out, ref, rtol=1e-6)


@pytest.mark.parametrize("seed", range(5))
def test_sarima_beats_seasonal_naive_on_trend_plus_season(nb, seed):
    # 20 seed của bản tham chiếu: tỉ lệ MAE SARIMA / seasonal naive từ 0.35 tới 0.88
    y = weekly_trend_series(seed)
    train, test = y[:-28], y[-28:]
    err_sarima = np.mean(np.abs(test - nb.sarima_forecast(train, 28)))
    err_naive = np.mean(np.abs(test - nb.seasonal_naive(train, 28)))
    assert err_sarima < err_naive


def test_backtest_mase_uses_only_the_past(nb):
    idx = pd.date_range("2018-01-01", periods=60, freq="D")
    series = pd.Series(np.arange(60.0), index=idx)
    seen = []

    def spy(train, h):
        seen.append((len(train), train[-1]))
        return np.zeros(h)

    cutoffs = [pd.Timestamp("2018-01-29"), pd.Timestamp("2018-02-12")]
    table = nb.backtest_mase(series, {"spy": spy}, cutoffs, h=7, m=7)
    assert seen == [(28, 27.0), (42, 41.0)]
    assert list(table.columns) == ["model", "cutoff", "mae", "mase"]
    # chuỗi tuyến tính: train[t] - train[t-7] = 7 → scale 7; test của origin đầu là 28..34 → MAE 31
    first = table.iloc[0]
    assert first["mae"] == pytest.approx(31.0)
    assert first["mase"] == pytest.approx(31.0 / 7)


def test_summarize(nb):
    table = pd.DataFrame({
        "model": ["seasonal_naive", "a", "seasonal_naive", "a", "seasonal_naive", "a"],
        "cutoff": pd.to_datetime(["2018-01-01"] * 2 + ["2018-01-15"] * 2 + ["2018-01-29"] * 2),
        "mae": [1.0] * 6,
        "mase": [1.0, 0.5, 1.0, 1.5, 1.0, 0.7],
    })
    out = nb.summarize(table)
    assert list(out.index) == ["a", "seasonal_naive"]
    assert out.loc["a", "mase_mean"] == pytest.approx(0.9)
    assert out.loc["a", "mase_median"] == pytest.approx(0.7)
    assert out.loc["a", "win_rate"] == pytest.approx(2 / 3)
    assert out.loc["seasonal_naive", "win_rate"] == 0


def test_real_olist(nb):
    orders = pd.read_csv(_olist_path())
    y = nb.daily_orders(orders)
    # Chuỗi 2017-01-09 → 2018-08-19 (mục 1 của README): 588 ngày, 97 845 đơn mọi trạng thái
    assert len(y) == 588 and y.sum() == 97845
    assert y.idxmax() == pd.Timestamp("2017-11-24") and y.max() == 1176
    table = nb.backtest_mase(y, {"seasonal_naive": nb.seasonal_naive, "sarima": nb.sarima_forecast}, CUTOFFS)
    out = nb.summarize(table)
    assert out.loc["seasonal_naive", "mase_mean"] == pytest.approx(1.261, abs=1e-3)
    assert out.loc["sarima", "mase_mean"] == pytest.approx(1.191, abs=0.02)


def _olist_path():
    path = ROOT / "data" / "raw" / "olist_orders_dataset.csv"
    if not path.exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    return path
