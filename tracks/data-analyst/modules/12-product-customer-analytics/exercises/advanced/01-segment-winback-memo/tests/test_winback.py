import re

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
START, END = pd.Timestamp("2011-06-01"), pd.Timestamp("2011-12-01")
MEMO_HEADINGS = ["## Trả lời ngắn", "## Phân khúc và bằng chứng", "## Đề xuất chiến dịch", "## Đo lường",
                 "## Giả định và giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("winback.ipynb")


def window_data():
    sales = pd.DataFrame([  # Customer ID, InvoiceDate, revenue
        (1.0, "2011-06-05 10:00", 100.0), (1.0, "2011-07-01 10:00", 50.0),
        (2.0, "2011-05-31 23:59", 999.0),                                   # trước cửa sổ
        (3.0, "2011-11-30 23:00", 40.0), (3.0, "2011-12-01 00:00", 777.0),  # mốc cuối không tính
        (6.0, "2011-07-01 10:00", 500.0),                                   # không có trong segments
        (None, "2011-07-02 10:00", 300.0),                                  # khách vãng lai
    ], columns=["Customer ID", "InvoiceDate", "revenue"])
    sales["InvoiceDate"] = pd.to_datetime(sales["InvoiceDate"])
    segments = pd.Series(["a", "a", "b", "b", "c"], index=[1.0, 2.0, 3.0, 4.0, 5.0], name="segment")
    return sales, segments


def test_segment_outcomes(nb):
    sales, segments = window_data()
    out = nb.segment_outcomes(sales, segments, START, END)
    assert list(out.columns) == ["customers", "active_share", "revenue", "revenue_per_customer", "revenue_share"]
    assert list(out.index) == ["a", "b", "c"], "Sắp theo doanh thu giảm dần"
    assert out.customers.tolist() == [2, 2, 1]
    assert out.active_share.tolist() == pytest.approx([0.5, 0.5, 0.0])
    assert out.revenue.tolist() == pytest.approx([150.0, 40.0, 0.0]), "Cửa sổ [start, end), chỉ khách có segment"
    assert out.revenue_per_customer.tolist() == pytest.approx([75.0, 20.0, 0.0]), "Chia cho mọi khách của segment"
    assert out.revenue_share.tolist() == pytest.approx([150 / 190, 40 / 190, 0.0])


def test_segment_outcomes_does_not_mutate_input(nb):
    sales, segments = window_data()
    before_s, before_g = sales.copy(), segments.copy()
    nb.segment_outcomes(sales, segments, START, END)
    pd.testing.assert_frame_equal(sales, before_s)
    pd.testing.assert_series_equal(segments, before_g)


def outcomes():
    return pd.DataFrame({"customers": [2, 2, 1], "active_share": [0.5, 0.5, 0.0], "revenue": [150.0, 40.0, 0.0]},
                        index=pd.Index(["a", "b", "c"], name="segment"))


def test_campaign_value_flat_uplift(nb):
    out = nb.campaign_value(outcomes(), uplift=0.1, margin=0.5, cost_per_customer=1.0)
    assert list(out.columns) == ["customers", "extra_gross_profit", "cost", "net"]
    assert list(out.index) == ["a", "b", "c"], "Sắp theo net giảm dần"
    # a: 2 khách × 10% × 150 GBP mỗi khách active × biên 50% = 15; b: 2 × 10% × 40 × 50% = 4; c: không ai active
    assert out.extra_gross_profit.tolist() == pytest.approx([15.0, 4.0, 0.0])
    assert out.cost.tolist() == pytest.approx([2.0, 2.0, 1.0])
    assert out.net.tolist() == pytest.approx([13.0, 2.0, -1.0])


def test_campaign_value_uplift_per_segment(nb):
    uplift = pd.Series({"a": 0.0, "b": 0.5})            # segment không có trong uplift: coi là 0
    out = nb.campaign_value(outcomes(), uplift=uplift, margin=0.5, cost_per_customer=1.0)
    assert list(out.index) == ["b", "c", "a"]
    assert out.loc["b", "extra_gross_profit"] == pytest.approx(20.0)
    assert out.loc["a", "net"] == pytest.approx(-2.0) and out.loc["c", "net"] == pytest.approx(-1.0)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 250 <= words <= 700, f"Memo 250-700 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
    assert "giả định" in memo.lower(), "Uplift, biên và chi phí là giả định: ghi rõ trong memo"
