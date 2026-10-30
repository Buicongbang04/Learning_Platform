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
    return ex.notebook("cohort_heatmap.ipynb")


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
    rows = [
        ("1", "2010-01-05", "A"), ("2", "2010-01-20", "A"), ("3", "2010-03-02", "A"),   # A: cohort 01, k = 0, 2
        ("4", "2010-02-10", "B"), ("5", "2010-03-15", "B"), ("6", "2010-05-01", "B"),   # B: cohort 02, k = 0, 1 (05 > last)
        ("7", "2010-01-31", "C"), ("8", "2010-02-01", "C"),                             # C: cohort 01, k = 0, 1
        ("9", "2010-03-10", "E"),                                                       # E: cohort 03, k = 0
        ("10", "2010-05-03", "D"),                                                      # D: cohort 05 > last: bỏ
        ("11", "2010-02-14", None),                                                     # khách vãng lai: bỏ
    ]
    out = pd.DataFrame(rows, columns=["Invoice", "InvoiceDate", "Customer ID"])
    out["InvoiceDate"] = pd.to_datetime(out["InvoiceDate"])
    out["revenue"] = 10.0
    return out


SMALL_LAST = M("2010-04")


def test_cohort_activity(nb):
    act = nb.cohort_activity(small_sales(), SMALL_LAST)
    assert list(act.columns) == ["customer_id", "month", "cohort", "k"]
    got = sorted((r.customer_id, str(r.month), str(r.cohort), int(r.k)) for r in act.itertuples())
    assert got == [
        ("A", "2010-01", "2010-01", 0), ("A", "2010-03", "2010-01", 2),
        ("B", "2010-02", "2010-02", 0), ("B", "2010-03", "2010-02", 1),
        ("C", "2010-01", "2010-01", 0), ("C", "2010-02", "2010-01", 1),
        ("E", "2010-03", "2010-03", 0),
    ], "Một dòng mỗi khách × tháng, chỉ tới tháng cuối, bỏ khách null"


def test_cohort_activity_does_not_mutate_input(nb):
    s = small_sales()
    before = s.copy()
    nb.cohort_activity(s, SMALL_LAST)
    pd.testing.assert_frame_equal(s, before)


def test_retention_matrix(nb):
    m = nb.retention_matrix(nb.cohort_activity(small_sales(), SMALL_LAST), SMALL_LAST)
    assert list(m.index) == [M("2010-01"), M("2010-02"), M("2010-03")]
    assert list(m.columns) == [0, 1, 2, 3], "Cột k từ 0 tới tuổi của cohort sớm nhất, kể cả k không ai mua"
    np.testing.assert_allclose(m.loc[M("2010-01")].to_numpy(), [1.0, 0.5, 0.5, 0.0])
    np.testing.assert_allclose(m.loc[M("2010-02")].to_numpy(), [1.0, 1.0, 0.0, np.nan])
    np.testing.assert_allclose(m.loc[M("2010-03")].to_numpy(), [1.0, 0.0, np.nan, np.nan])


def test_calendar_view(nb):
    m = nb.retention_matrix(nb.cohort_activity(small_sales(), SMALL_LAST), SMALL_LAST)
    cal = nb.calendar_view(m)
    assert list(cal.columns) == [M("2010-02"), M("2010-03"), M("2010-04")], "Bỏ k = 0; cột là tháng lịch cohort + k"
    np.testing.assert_allclose(cal.loc[M("2010-01")].to_numpy(), [0.5, 0.5, 0.0])
    np.testing.assert_allclose(cal.loc[M("2010-02")].to_numpy(), [np.nan, 1.0, 0.0])
    np.testing.assert_allclose(cal.loc[M("2010-03")].to_numpy(), [np.nan, np.nan, 0.0])


def test_retention_curve(nb):
    m = nb.retention_matrix(nb.cohort_activity(small_sales(), SMALL_LAST), SMALL_LAST)
    sizes = pd.Series({M("2010-01"): 2, M("2010-02"): 1, M("2010-03"): 1})
    curve = nb.retention_curve(m, sizes, min_cohorts=2)
    assert list(curve.columns) == ["weighted", "simple", "cohorts"]
    assert curve.cohorts.tolist() == [3, 3, 2, 1]
    assert curve.weighted.iloc[:3].tolist() == pytest.approx([1.0, 0.5, 1 / 3]), "Trọng số = cỡ cohort đã quan sát"
    assert curve.simple.iloc[:3].tolist() == pytest.approx([1.0, 0.5, 0.25])
    assert curve.weighted.isna().tolist() == [False, False, False, True], "Dưới min_cohorts thì để trống"
    assert np.isnan(curve.simple.iloc[3])


@pytest.fixture(scope="module")
def real_sales():
    old, new = read_sheet("Year 2009-2010"), read_sheet("Year 2010-2011")
    return clean_sales(pd.concat([old[old.InvoiceDate < "2010-12-01"], new], ignore_index=True))


def test_real_cohorts(nb, real_sales):
    act = nb.cohort_activity(real_sales, LAST)
    m = nb.retention_matrix(act, LAST)
    sizes = act[act.k == 0].groupby("cohort").size()
    assert len(m) == 24 and sizes.sum() == 5_850
    assert int(m.notna().sum().sum()) == 300, "Tam giác: cohort tuổi a có a + 1 ô quan sát được"
    assert m.loc[M("2010-01"), 1] == pytest.approx(0.2063, abs=1e-4)
    assert m.loc[M("2011-04"), 1] == pytest.approx(0.2547, abs=1e-4)
    assert m[1].idxmin() == M("2010-12")
    cal = nb.calendar_view(m)
    assert cal.columns.min() == M("2010-01") and cal.columns.max() == LAST and cal.shape[1] == 23
    assert cal.loc[M("2010-01"), M("2010-11")] == pytest.approx(0.3029, abs=1e-4)
    assert cal.loc[M("2010-01"), M("2010-12")] == pytest.approx(0.1723, abs=1e-4)
    curve = nb.retention_curve(m, sizes)
    assert curve.loc[1, "weighted"] == pytest.approx(0.2345, abs=1e-4)
    assert curve.loc[12, "weighted"] == pytest.approx(0.2269, abs=1e-4)
    assert curve.loc[21, "cohorts"] == 3 and np.isnan(curve.loc[22, "weighted"])
