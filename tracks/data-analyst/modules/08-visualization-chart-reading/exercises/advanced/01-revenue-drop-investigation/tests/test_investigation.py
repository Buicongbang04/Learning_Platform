import re

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Trả lời ngắn", "## Bằng chứng", "### Chart 1", "### Chart 2", "### Chart 3",
                 "## Kết luận", "## Việc cần làm", "## Giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("investigation.ipynb")


def frame(rows):
    out = pd.DataFrame(rows, columns=["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"])
    out["InvoiceDate"] = pd.to_datetime(out["InvoiceDate"])
    return out


def cancel_tx():
    nan = np.nan
    return frame([
        (1, "A", 5, "2011-12-09 09:00", 2.0, 10.0, "UK"),        # 0: bị C1 huỷ (dòng mua muộn nhất trước C1)
        (2, "A", 5, "2011-12-09 08:00", 2.0, 10.0, "UK"),        # 1: cũng khớp nhưng sớm hơn dòng 0
        ("C1", "A", -5, "2011-12-09 09:10", 2.0, 10.0, "UK"),    # 2: dòng huỷ
        (3, "B", 3, "2011-12-09 10:00", 1.0, 11.0, "UK"),        # 3: huỷ C2 xảy ra trước lúc mua
        ("C2", "B", -3, "2011-12-09 09:00", 1.0, 11.0, "UK"),    # 4
        (4, "A", 2, "2011-12-09 09:00", 2.0, 12.0, "UK"),        # 5: C3 là khách khác
        ("C3", "A", -2, "2011-12-09 09:30", 2.0, 13.0, "UK"),    # 6
        (5, "A", 7, "2011-12-09 09:00", 2.0, nan, "UK"),         # 7: khách vãng lai, không ghép được
        ("C4", "A", -7, "2011-12-09 09:30", 2.0, nan, "UK"),     # 8
        (6, "D", 4, "2011-12-09 09:00", 3.0, 14.0, "UK"),        # 9: huỷ một phần (2/4) không tính
        ("C5", "D", -2, "2011-12-09 09:30", 3.0, 14.0, "UK"),    # 10
        (7, "E", 1, "2011-12-09 09:00", 0.0, 15.0, "UK"),        # 11: giá 0, không phải dòng mua hợp lệ
        ("C6", "E", -1, "2011-12-09 09:30", 0.0, 15.0, "UK"),    # 12
        (8, "F", 9, "2011-12-01 09:00", 1.5, 16.0, "France"),    # 13: huỷ ngày hôm sau vẫn tính
        ("C7", "F", -9, "2011-12-02 15:00", 1.5, 16.0, "France"),  # 14
    ])


def test_reversed_lines(nb):
    out = nb.reversed_lines(cancel_tx())
    assert isinstance(out, pd.Series) and out.dtype == bool
    assert out.name == "reversed"
    assert list(out.index) == list(range(15))
    assert sorted(out[out].index) == [0, 13]


def test_reversed_lines_does_not_mutate_input(nb):
    tx = cancel_tx()
    before = tx.copy()
    nb.reversed_lines(tx)
    pd.testing.assert_frame_equal(tx, before)


def type_data():
    nan = np.nan
    history = frame([
        (100, "A", 1, "2010-11-05 10:00", 1.0, 1.0, "UK"),       # khách 1 đã mua trước
        ("C101", "A", -1, "2010-10-01 10:00", 1.0, 3.0, "UK"),  # khách 3 chỉ có đơn huỷ: chưa từng mua
        (102, "A", 1, "2010-10-01 10:00", 0.0, 4.0, "UK"),      # khách 4 chỉ có dòng giá 0: chưa từng mua
    ])
    tx = frame([
        (1, "A", 2, "2011-01-03 10:00", 1.0, 1.0, "UK"),        # 0 returning
        (2, "A", 2, "2011-01-10 10:00", 1.0, 2.0, "UK"),        # 1 new
        (3, "A", 2, "2011-01-20 10:00", 1.0, 2.0, "UK"),        # 2 new (cùng tháng lần đầu)
        (4, "A", 2, "2011-02-02 10:00", 1.0, 2.0, "UK"),        # 3 returning
        (5, "A", 2, "2011-01-05 10:00", 1.0, 3.0, "UK"),        # 4 new
        (6, "A", 2, "2011-01-06 10:00", 1.0, nan, "UK"),        # 5 guest
        (7, "A", -1, "2011-01-07 10:00", 1.0, 2.0, "UK"),       # 6 không hợp lệ: không có trong kết quả
        (8, "A", 2, "2011-02-01 10:00", 1.0, 4.0, "UK"),        # 7 new
    ])
    return tx, history


def test_customer_type(nb):
    tx, history = type_data()
    out = nb.customer_type(tx, history)
    assert list(out.index) == [0, 1, 2, 3, 4, 5, 7]
    assert out["customer_type"].tolist() == ["returning", "new", "new", "returning", "new", "guest", "new"]
    assert out["revenue"].tolist() == pytest.approx([2.0] * 7)
    assert set(tx.columns) <= set(out.columns)


def test_customer_type_does_not_mutate_input(nb):
    tx, history = type_data()
    before_tx, before_hist = tx.copy(), history.copy()
    nb.customer_type(tx, history)
    pd.testing.assert_frame_equal(tx, before_tx)
    pd.testing.assert_frame_equal(history, before_hist)


def bridge_rows():
    return pd.DataFrame({
        "InvoiceDate": pd.to_datetime(["2011-01-01 08:00", "2011-01-05 08:00", "2011-01-09 23:59", "2011-01-10 00:00",
                                       "2011-02-01 08:00", "2011-02-03 08:00", "2011-02-09 08:00", "2011-02-15 08:00"]),
        "revenue": [100.0, 50.0, 30.0, 999.0, 80.0, 75.0, 40.0, 999.0],
        "Country": ["UK", "France", "Japan", "UK", "UK", "France", "Germany", "UK"],
    })


def test_revenue_bridge(nb):
    out = nb.revenue_bridge(bridge_rows(), ("2011-01-01", "2011-01-10"), ("2011-02-01", "2011-02-10"), "Country")
    assert list(out.columns) == ["a", "b", "diff", "share_of_diff"]
    assert out.index.name == "Country"
    # a: UK 100, France 50, Japan 30 (dòng 10/01 00:00 nằm ngoài); b: UK 80, France 75, Germany 40
    assert list(out.index) == ["Germany", "Japan", "France", "UK"]
    assert out.loc["Japan", ["a", "b", "diff"]].tolist() == pytest.approx([30.0, 0.0, -30.0])
    assert out.loc["Germany", ["a", "b", "diff"]].tolist() == pytest.approx([0.0, 40.0, 40.0])
    assert out["diff"].sum() == pytest.approx(195.0 - 180.0)
    assert out.loc["Germany", "share_of_diff"] == pytest.approx(40.0 / 15.0)
    assert out["share_of_diff"].sum() == pytest.approx(1.0)


def test_revenue_bridge_does_not_mutate_input(nb):
    rows = bridge_rows()
    before = rows.copy()
    nb.revenue_bridge(rows, ("2011-01-01", "2011-01-10"), ("2011-02-01", "2011-02-10"), "Country")
    pd.testing.assert_frame_equal(rows, before)


@pytest.fixture(scope="module")
def real_tx():
    path = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    return pd.read_excel(path, sheet_name="Year 2010-2011")


def test_real_reversed_and_bridge(nb, real_tx):
    flag = nb.reversed_lines(real_tx)
    assert flag.sum() == 2860
    rows = nb.clean(real_tx)
    rows = rows.assign(reversed=flag.loc[rows.index])
    dec11 = rows[(rows.InvoiceDate >= "2011-12-01") & (rows.InvoiceDate < "2011-12-10")]
    assert dec11.revenue.sum() == pytest.approx(638_811.0, abs=1)
    assert dec11.revenue[dec11.reversed].sum() == pytest.approx(169_357.0, abs=1)
    kept = rows[~rows.reversed]
    bridge = nb.revenue_bridge(kept, ("2010-12-01", "2010-12-10"), ("2011-12-01", "2011-12-10"), "Country")
    assert bridge["a"].sum() == pytest.approx(436_870.0, abs=1)
    assert bridge["b"].sum() == pytest.approx(469_453.0, abs=1)
    assert list(bridge.index[:2]) == ["United Kingdom", "Netherlands"]
    assert bridge.loc["United Kingdom", "diff"] == pytest.approx(20_318.0, abs=1)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo một trang: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
