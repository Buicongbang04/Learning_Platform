import tempfile
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
LAST = pd.Period("2011-11", "M")
M = lambda s: pd.Period(s, "M")  # noqa: E731


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ltv_payback.ipynb")


# Loader Online Retail II của module 12: chép y hệt ở mọi bài dùng bộ này; sửa thì sửa mọi bản.
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"  # cache parquet trong thư mục tạm, không ghi vào data/raw


def read_sheet(sheet: str) -> pd.DataFrame:
    """Một sheet Online Retail II. Lần đầu đọc xlsx (30-90 giây) rồi ghi cache parquet theo mtime và cỡ tệp."""
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_II-{sheet.replace(' ', '_')}-{stat.st_mtime_ns}-{stat.st_size}.parquet"
    if cache.exists():
        try:
            return pd.read_parquet(cache)
        except (OSError, ValueError):  # cache hỏng: đọc lại từ xlsx và ghi đè
            pass
    tx = pd.read_excel(xlsx, sheet_name=sheet)
    tx = tx.assign(Invoice=tx["Invoice"].astype(str), StockCode=tx["StockCode"].astype(str),
                   Description=tx["Description"].astype("string"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{uuid.uuid4().hex}.tmp")  # ghi atomic: tệp tạm rồi đổi tên
    tx.to_parquet(tmp, index=False)
    tmp.replace(cache)
    return tx


def clean_sales(tx: pd.DataFrame) -> pd.DataFrame:
    """Dòng hợp lệ theo định nghĩa dùng chung của track, kèm revenue = Quantity * Price."""
    s = tx.assign(Invoice=tx["Invoice"].astype(str))
    s = s[~s.Invoice.str.startswith("C") & (s.Quantity > 0) & (s.Price > 0)].copy()
    s["revenue"] = s.Quantity * s.Price
    return s


def small_sales():
    rows = [  # InvoiceDate, Customer ID, revenue
        ("2010-01-05", "A", 100.0), ("2010-03-02", "A", 50.0),                         # cohort 01
        ("2010-01-31", "C", 20.0), ("2010-02-01", "C", 30.0),                          # cohort 01
        ("2010-02-10", "B", 40.0), ("2010-03-15", "B", 10.0), ("2010-05-01", "B", 999.0),  # cohort 02; 05 > last
        ("2010-03-10", "E", 70.0),                                                     # cohort 03
        ("2010-02-14", None, 500.0),                                                   # khách vãng lai: bỏ
    ]
    out = pd.DataFrame(rows, columns=["InvoiceDate", "Customer ID", "revenue"])
    out["InvoiceDate"] = pd.to_datetime(out["InvoiceDate"])
    return out


SMALL_LAST = M("2010-04")


def test_simple_ltv(nb):
    assert nb.simple_ltv(50, 6, 0.4, 0.6) == pytest.approx(300.0)
    assert nb.simple_ltv(100, 1, 0.5, 0.0) == pytest.approx(50.0)
    for bad in (1.0, -0.1):
        with pytest.raises(ValueError):
            nb.simple_ltv(50, 6, 0.4, bad)


def test_cohort_ltv(nb):
    ltv = nb.cohort_ltv(small_sales(), SMALL_LAST)
    assert list(ltv.index) == [M("2010-01"), M("2010-02"), M("2010-03")]
    assert list(ltv.columns) == [0, 1, 2, 3], "Cột k đủ từ 0 tới tuổi cohort sớm nhất"
    np.testing.assert_allclose(ltv.loc[M("2010-01")].to_numpy(), [60.0, 75.0, 100.0, 100.0])
    np.testing.assert_allclose(ltv.loc[M("2010-02")].to_numpy(), [40.0, 50.0, 50.0, np.nan])
    np.testing.assert_allclose(ltv.loc[M("2010-03")].to_numpy(), [70.0, 70.0, np.nan, np.nan])


def test_cohort_ltv_does_not_mutate_input(nb):
    s = small_sales()
    before = s.copy()
    nb.cohort_ltv(s, SMALL_LAST)
    pd.testing.assert_frame_equal(s, before)


def test_payback_month(nb):
    ltv = nb.cohort_ltv(small_sales(), SMALL_LAST)
    out = nb.payback_month(ltv, cac=30, margin=0.5)        # cần doanh thu luỹ kế 60
    assert out.name == "payback_month" and str(out.dtype) == "Int64"
    assert out.tolist()[0] == 0 and out.tolist()[2] == 0
    assert pd.isna(out.iloc[1]), "Chưa hoàn vốn trong các tháng đã quan sát: NA"
    later = nb.payback_month(ltv, cac=35, margin=0.5)       # cần 70
    assert later.iloc[0] == 1 and later.iloc[2] == 0


def test_max_cac_table(nb):
    ltv = nb.cohort_ltv(small_sales(), SMALL_LAST)
    sizes = pd.Series({M("2010-01"): 2, M("2010-02"): 1, M("2010-03"): 1})
    out = nb.max_cac_table(ltv, sizes, margins=[0.2, 0.5], horizons=[1, 2, 3])
    assert list(out.index) == [1, 2, 3] and list(out.columns) == [0.2, 0.5]
    # h tháng = cột k = h - 1; trung bình theo cỡ cohort, chỉ cohort đã quan sát được
    np.testing.assert_allclose(out[0.5].to_numpy(), [57.5 * 0.5, 67.5 * 0.5, 250 / 3 * 0.5])
    np.testing.assert_allclose(out[0.2].to_numpy(), [57.5 * 0.2, 67.5 * 0.2, 250 / 3 * 0.2])


@pytest.fixture(scope="module")
def real_sales():
    old, new = read_sheet("Year 2009-2010"), read_sheet("Year 2010-2011")
    return clean_sales(pd.concat([old[old.InvoiceDate < "2010-12-01"], new], ignore_index=True))


def test_real_ltv(nb, real_sales):
    ltv = nb.cohort_ltv(real_sales, LAST)
    assert ltv.shape == (24, 24)
    assert ltv.loc[M("2010-01"), 0] == pytest.approx(422.70, abs=0.01)
    assert ltv.loc[M("2010-01"), 11] == pytest.approx(2043.16, abs=0.01)
    assert np.isnan(ltv.loc[M("2011-06"), 6])
    payback = nb.payback_month(ltv, cac=200, margin=0.35)
    assert payback[M("2010-09")] == 0 and payback[M("2010-12")] == 4 and payback[M("2010-04")] == 3
    late = nb.payback_month(ltv, cac=400, margin=0.35)
    assert pd.isna(late[M("2010-11")]) and late[M("2010-05")] == 13
    sizes = nb.cohort_sizes(real_sales)
    table = nb.max_cac_table(ltv.loc[M("2010-01"):], sizes, margins=[0.35], horizons=[3, 6, 12])
    assert table[0.35].tolist() == pytest.approx([234.82, 332.32, 502.24], abs=0.01)
