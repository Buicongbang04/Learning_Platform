import tempfile
import uuid
from pathlib import Path

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
SNAPSHOT = pd.Timestamp("2011-12-10")


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("rfm_segments.ipynb")


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
    rows = [  # Invoice, InvoiceDate, Customer ID, revenue
        ("1", "2011-12-09 15:00", 1.0, 100.0), ("1", "2011-12-09 15:00", 1.0, 50.0),   # cùng hoá đơn: 1 đơn
        ("2", "2011-11-01 10:00", 1.0, 30.0),
        ("3", "2011-11-25 23:59", 2.0, 10.0),                                          # recency 15 ngày
        ("4", "2011-06-01 08:00", 3.0, 5.0), ("5", "2011-05-01 08:00", 3.0, 5.0),
        ("6", "2011-07-01 08:00", None, 999.0),                                        # khách vãng lai: bỏ
    ]
    out = pd.DataFrame(rows, columns=["Invoice", "InvoiceDate", "Customer ID", "revenue"])
    out["InvoiceDate"] = pd.to_datetime(out["InvoiceDate"])
    return out


def test_rfm_table(nb):
    rfm = nb.rfm_table(small_sales(), SNAPSHOT)
    assert list(rfm.columns) == ["recency", "frequency", "monetary"]
    assert sorted(rfm.index) == [1.0, 2.0, 3.0]
    assert rfm.loc[1.0].tolist() == pytest.approx([1, 2, 180.0]), "Recency tính theo ngày (bỏ giờ); F đếm hoá đơn khác nhau"
    assert rfm.loc[2.0].tolist() == pytest.approx([15, 1, 10.0])
    assert rfm.loc[3.0].tolist() == pytest.approx([192, 2, 10.0])


def test_rfm_table_does_not_mutate_input(nb):
    s = small_sales()
    before = s.copy()
    nb.rfm_table(s, SNAPSHOT)
    pd.testing.assert_frame_equal(s, before)


def test_score_rfm_thresholds(nb):
    rfm = pd.DataFrame({
        "recency": [0, 14, 15, 30, 31, 90, 91, 180, 181, 400],
        "frequency": [1, 2, 3, 4, 5, 9, 10, 40, 1, 2],
        "monetary": [10.0, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    }, index=pd.Index(range(10), name="customer_id"))
    out = nb.score_rfm(rfm)
    assert list(out.columns) == ["recency", "frequency", "monetary", "R", "F", "M"]
    assert out.R.tolist() == [5, 5, 4, 4, 3, 3, 2, 2, 1, 1]
    assert out.F.tolist() == [1, 2, 3, 3, 4, 4, 5, 5, 1, 2]
    assert out.M.tolist() == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5], "M theo quintile của monetary"
    assert "R" not in rfm.columns, "Không sửa bảng đầu vào"


def test_score_rfm_ties_split_by_rank(nb):
    rfm = pd.DataFrame({"recency": [1] * 5, "frequency": [1] * 5, "monetary": [5.0] * 5})
    assert sorted(nb.score_rfm(rfm).M.tolist()) == [1, 2, 3, 4, 5], "Giá trị trùng: xếp hạng method='first'"


def test_assign_segment(nb):
    scores = pd.DataFrame({"R": [5, 5, 3, 1, 2, 4], "F": [5, 1, 4, 5, 1, 1]}, index=list("abcdef"))
    rules = [("champions", [5], [4, 5]), ("loyal", [3, 4], [4, 5]), ("new", [5], [1]), ("cant_lose", [1, 2], [5])]
    out = nb.assign_segment(scores, rules)
    assert out.name == "segment"
    assert list(out.index) == list("abcdef")
    assert out.tolist() == ["champions", "new", "loyal", "cant_lose", "other", "other"]
    first_wins = nb.assign_segment(scores.iloc[:1], [("a", [5], [5]), ("b", [5], [5])])
    assert first_wins.tolist() == ["a"], "Luật đầu tiên khớp thắng"


def test_segment_summary(nb):
    rfm = pd.DataFrame({"recency": [1, 3, 100, 200], "frequency": [5, 7, 1, 2], "monetary": [100.0, 300, 50, 50]})
    seg = pd.Series(["top", "top", "low", "low"], name="segment")
    out = nb.segment_summary(rfm, seg)
    assert list(out.columns) == ["customers", "revenue", "median_recency", "median_frequency",
                                 "customer_share", "revenue_share"]
    assert list(out.index) == ["top", "low"], "Sắp theo doanh thu giảm dần"
    assert out.loc["top"].tolist() == pytest.approx([2, 400.0, 2.0, 6.0, 0.5, 0.8])
    assert out.loc["low", "revenue_share"] == pytest.approx(0.2)


@pytest.fixture(scope="module")
def real_sales():
    return clean_sales(read_sheet("Year 2010-2011"))


def test_real_rfm(nb, real_sales):
    rfm = nb.rfm_table(real_sales, SNAPSHOT)
    assert len(rfm) == 4_338
    assert rfm.monetary.sum() == pytest.approx(8_911_425.9, abs=1)
    scores = nb.score_rfm(rfm)
    assert scores.R.value_counts().sort_index().tolist() == [861, 588, 1261, 760, 868]
    assert scores.F.value_counts().sort_index().tolist() == [1493, 835, 896, 723, 391]
    seg = nb.assign_segment(scores, nb.SEGMENTS)
    summary = nb.segment_summary(rfm, seg)
    assert summary.index[0] == "champions"
    assert summary.loc["champions", "customers"] == 507
    assert summary.loc["champions", "revenue_share"] == pytest.approx(0.4676, abs=1e-4)
    assert summary.loc["hibernating", "customers"] == 1_164
    assert summary.loc["at_risk", "customers"] == 278
    assert int((scores.M[seg == "at_risk"] >= 4).sum()) == 142
