import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


# Đọc sheet xlsx mất 20-90 giây: cache parquet trong thư mục tạm của hệ điều hành (không ghi vào data/raw),
# khoá theo mtime + size của tệp xlsx, ghi atomic. Cache giữ dữ liệu gốc của sheet (chưa làm sạch); Invoice,
# StockCode, Description ép str để ghi được parquet.
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"


def read_retail_sheet(sheet: str = "Year 2010-2011") -> pd.DataFrame:
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_II-{sheet.replace(' ', '_')}-{stat.st_mtime_ns}-{stat.st_size}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    tx = pd.read_excel(xlsx, sheet_name=sheet)
    tx = tx.assign(Invoice=tx["Invoice"].astype(str), StockCode=tx["StockCode"].astype(str),
                   Description=tx["Description"].astype("string"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
    tx.to_parquet(tmp, index=False)
    os.replace(tmp, cache)
    return tx
WEEK_COLUMNS = ["revenue", "trading_days", "calendar_days", "complete", "rolling_4w"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("retail_calendar.ipynb")


def tiny_tx():
    # Thứ Tư 02/03/2011 tới Thứ Hai 14/03/2011; Invoice trộn int và str như khi đọc từ Excel.
    # Có đơn huỷ, dòng giá 0, dòng số lượng âm; ngày 05, 06, 12 không có đơn hợp lệ.
    return pd.DataFrame({
        "Invoice": [1, 1, 2, "C3", 4, 5, 6, 7, 8, 9, 10],
        "InvoiceDate": pd.to_datetime([
            "2011-03-02 09:00", "2011-03-02 09:00", "2011-03-03 10:00", "2011-03-03 11:00", "2011-03-04 12:00",
            "2011-03-05 13:00", "2011-03-07 08:30", "2011-03-09 15:00", "2011-03-11 16:00", "2011-03-13 10:00",
            "2011-03-14 17:45",
        ]),
        "Quantity": [10, 5, 4, -4, 2, 3, 6, 1, 2, -1, 8],
        "Price": [2.0, 4.0, 5.0, 5.0, 10.0, 0.0, 5.0, 20.0, 15.0, 3.0, 2.5],
        "Customer ID": [1.0, 1.0, 2.0, 2.0, np.nan, 3.0, 1.0, 2.0, 4.0, 4.0, 5.0],
    })


def test_clean_sales(nb):
    tx = tiny_tx()
    before = tx.copy()
    sales = nb.clean_sales(tx)
    pd.testing.assert_frame_equal(tx, before)
    assert sales["Invoice"].tolist() == ["1", "1", "2", "4", "6", "7", "8", "10"]
    assert sales["revenue"].tolist() == pytest.approx([20.0, 20.0, 20.0, 20.0, 30.0, 20.0, 30.0, 20.0])


def test_daily_revenue_fills_calendar(nb):
    daily = nb.daily_revenue(tiny_tx())
    assert daily.name == "revenue"
    assert daily.index.name == "date"
    assert daily.index.freqstr == "D"
    assert daily.index[0] == pd.Timestamp("2011-03-02") and daily.index[-1] == pd.Timestamp("2011-03-14")
    assert len(daily) == 13
    expected = [40, 20, 20, 0, 0, 30, 0, 20, 0, 30, 0, 0, 20]
    assert daily.tolist() == pytest.approx(expected)


def test_daily_average(nb):
    out = nb.daily_average(nb.daily_revenue(tiny_tx()))
    assert out.name == "daily_average"
    assert list(out.index) == ["calendar_days", "trading_days", "per_calendar_day", "per_trading_day"]
    assert out.tolist() == pytest.approx([13, 7, 180 / 13, 180 / 7])


def test_weekly_report(nb):
    weekly = nb.weekly_report(nb.daily_revenue(tiny_tx()))
    assert list(weekly.columns) == WEEK_COLUMNS
    assert weekly.index.name == "week_end"
    assert list(weekly.index) == list(pd.to_datetime(["2011-03-06", "2011-03-13", "2011-03-20"]))
    assert weekly["revenue"].tolist() == pytest.approx([80.0, 80.0, 20.0])
    assert weekly["trading_days"].tolist() == [3, 3, 1]
    assert weekly["calendar_days"].tolist() == [5, 7, 1]
    assert weekly["complete"].tolist() == [False, True, False]
    assert weekly["rolling_4w"].isna().all()


def test_weekly_rolling_skips_incomplete_weeks(nb):
    days = pd.date_range("2011-01-05", "2011-02-17", freq="D", name="date")   # Thứ Tư tới Thứ Năm
    daily = pd.Series(10.0, index=days, name="revenue")
    weekly = nb.weekly_report(daily)
    assert weekly["calendar_days"].tolist() == [5, 7, 7, 7, 7, 7, 4]
    assert weekly["complete"].tolist() == [False, True, True, True, True, True, False]
    rolling = weekly["rolling_4w"].tolist()
    assert all(np.isnan(rolling[i]) for i in [0, 1, 2, 3, 6])
    assert rolling[4:6] == pytest.approx([70.0, 70.0])


@pytest.fixture(scope="module")
def real_tx():
    return read_retail_sheet("Year 2010-2011")


_DAILY = {}


def real_daily(nb, real_tx):
    """Tính một lần; gọi trong thân test để starter FAIL chứ không ERROR."""
    if "daily" not in _DAILY:
        _DAILY["daily"] = nb.daily_revenue(real_tx)
    return _DAILY["daily"]


def test_real_daily(nb, real_tx):
    daily = real_daily(nb, real_tx)
    assert len(daily) == 374
    assert daily.sum() == pytest.approx(10_666_702.54, abs=1)
    zero = daily[daily == 0]
    assert len(zero) == 69
    assert int((zero.index.day_of_week == 5).sum()) == 53
    out = nb.daily_average(daily)
    assert out["trading_days"] == 305
    assert out["per_calendar_day"] == pytest.approx(28_520.60, abs=0.5)
    assert out["per_trading_day"] == pytest.approx(34_972.80, abs=0.5)


def test_real_weekly(nb, real_tx):
    weekly = nb.weekly_report(real_daily(nb, real_tx))
    assert len(weekly) == 54
    assert int(weekly["complete"].sum()) == 52
    last = weekly.iloc[-1]
    assert weekly.index[-1] == pd.Timestamp("2011-12-11")
    assert (last["calendar_days"], bool(last["complete"])) == (5, False)
    assert last["revenue"] == pytest.approx(504_327.93, abs=1)
    best = weekly[weekly["complete"]]["revenue"].idxmax()
    assert best == pd.Timestamp("2011-11-20")
    assert weekly.loc["2011-12-04", "rolling_4w"] == pytest.approx(349_862.60, abs=1)
    assert weekly.loc["2011-01-02", "rolling_4w"] == pytest.approx(159_579.58, abs=1)
