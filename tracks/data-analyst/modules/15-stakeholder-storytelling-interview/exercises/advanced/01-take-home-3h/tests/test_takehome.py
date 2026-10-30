import re

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
HEADINGS = ["## Tóm tắt cho người ra quyết định", "## Giả định", "## Phương pháp", "## Kết quả", "## Khuyến nghị",
            "## Giới hạn", "## Nếu có thêm thời gian", "## Nhật ký thời gian"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("takehome.ipynb")


def raw_tx():
    nan = np.nan
    rows = [
        # Invoice, StockCode, Quantity, Price, Customer ID
        ("536365", "85123A", 6, 2.55, 17850.0),       # 0 giữ
        ("536365", "post", 1, 18.0, 17850.0),         # 1 phí
        ("C536379", "22423", -1, 12.75, 14527.0),     # 2 huỷ
        ("536380", " 22423 ", 2, 12.75, 14527.0),     # 3 giữ, StockCode chuẩn hoá
        ("536381", "85123a", 3, 2.55, nan),           # 4 giữ, chữ thường -> 85123A
        ("536382", "15056BL", 1, 5.95, 13047.0),      # 5 giữ, hậu tố 2 chữ
        ("536383", "gift_0001_20", 1, 16.67, nan),    # 6 phiếu quà, không phải hàng
        ("536384", "21730", 0, 4.25, 13047.0),        # 7 Quantity 0
        ("536385", "21730", 4, 0.0, 13047.0),         # 8 giá 0
        ("536386", "AMAZONFEE", 1, 100.0, nan),       # 9 phí
        (536387, 21730, 2, 4.25, 12583.0),            # 10 giữ: Invoice và StockCode đọc thành số
        ("536388", "1234", 1, 1.0, 12583.0),          # 11 4 chữ số: không phải mã hàng
    ]
    df = pd.DataFrame(rows, columns=["Invoice", "StockCode", "Quantity", "Price", "Customer ID"])
    df["InvoiceDate"] = pd.Timestamp("2011-01-05")
    df["Country"] = "United Kingdom"
    return df


def test_clean_product_lines(nb):
    tx = raw_tx()
    before = tx.copy()
    out = nb.clean_product_lines(tx)
    pd.testing.assert_frame_equal(tx, before)
    assert sorted(out.index) == [0, 3, 4, 5, 10]
    assert out.loc[[0, 3, 4, 5, 10], "StockCode"].tolist() == ["85123A", "22423", "85123A", "15056BL", "21730"]
    assert out.loc[10, "Invoice"] == "536387"
    assert out.loc[3, "revenue"] == pytest.approx(25.5)
    assert out["revenue"].sum() == pytest.approx(15.3 + 25.5 + 7.65 + 5.95 + 8.5)


def sales():
    # doanh thu: A 10+5+10 = 25; B 2+4 = 6; C 6+3 = 9; D 50 (khách thiếu mã). Tổng 90.
    # theo khách: 1 -> 12, 2 -> 9, 3 -> 16, 4 -> 3 (tổng có mã 40)
    nan = np.nan
    return pd.DataFrame({
        "Invoice": ["1", "1", "2", "3", "3", "4", "5", "6"],
        "StockCode": ["A", "B", "A", "C", "A", "D", "C", "B"],
        "Quantity": [10, 1, 5, 2, 10, 1, 1, 2],
        "Price": [1.0, 2.0, 1.0, 3.0, 1.0, 50.0, 3.0, 2.0],
        "Customer ID": [1.0, 1.0, 2.0, 3.0, 3.0, nan, 4.0, 2.0],
    })


def test_sku_table(nb):
    s = sales()
    before = s.copy()
    t = nb.sku_table(s)
    pd.testing.assert_frame_equal(s, before)
    assert list(t.columns) == ["revenue", "units", "invoices", "customers"]
    assert list(t.index) == ["D", "A", "C", "B"]
    assert t.loc["A"].tolist() == pytest.approx([25.0, 25, 3, 3])
    assert t.loc["D", "customers"] == 0
    assert t.loc["B", "invoices"] == 2 and t.loc["B", "customers"] == 2


def test_sku_table_ties_by_code(nb):
    s = pd.DataFrame({"Invoice": ["1", "2"], "StockCode": ["Z", "Y"], "Quantity": [1, 1], "Price": [5.0, 5.0],
                      "Customer ID": [1.0, 2.0]})
    assert list(nb.sku_table(s).index) == ["Y", "Z"]


def test_cut_impact(nb):
    s = sales()
    before = s.copy()
    out = nb.cut_impact(s, ["B", "C", "ZZZ"])
    pd.testing.assert_frame_equal(s, before)
    assert out["skus_cut"] == 2
    assert out["revenue_lost_share"] == pytest.approx(15 / 90)
    assert out["customers_affected"] == 4          # B: khách 1, 2; C: khách 3, 4
    assert out["customers_affected_share"] == pytest.approx(1.0)
    assert out["affected_customers_revenue_share"] == pytest.approx(1.0)
    one = nb.cut_impact(s, ["D"])                   # chỉ khách thiếu mã mua D
    assert one["customers_affected"] == 0 and one["affected_customers_revenue_share"] == pytest.approx(0.0)
    assert one["revenue_lost_share"] == pytest.approx(50 / 90)
    b = nb.cut_impact(s, ["B"])
    assert b["customers_affected"] == 2 and b["customers_affected_share"] == pytest.approx(0.5)
    assert b["affected_customers_revenue_share"] == pytest.approx(21 / 40)


# ---------- SUBMISSION.md ----------

@pytest.fixture(scope="module")
def submission():
    return ex.read("SUBMISSION.md")


def section(text, heading):
    start = text.index(heading) + len(heading)
    nxt = text.find("\n## ", start)
    return text[start:] if nxt == -1 else text[start:nxt]


def test_submission_complete(submission):
    assert "TODO" not in submission, "Còn dòng TODO trong SUBMISSION.md"
    words = len(submission.split())
    assert 400 <= words <= 1200, f"400-1200 từ, hiện có {words}"
    title = submission.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline có con số"
    pos = [submission.find(h) for h in HEADINGS]
    assert all(p >= 0 for p in pos), f"Thiếu mục: {[h for h, p in zip(HEADINGS, pos) if p < 0]}"
    assert pos == sorted(pos), "Các mục phải theo đúng thứ tự của khung"


def test_summary_is_short_with_numbers(submission):
    summary = section(submission, HEADINGS[0])
    assert len(summary.split()) <= 150, "Tóm tắt tối đa 150 từ"
    assert len(re.findall(r"\d+(?:[.,]\d+)?", summary)) >= 3, "Tóm tắt cần ít nhất ba con số"


def test_assumptions_listed(submission):
    bullets = [l for l in section(submission, "## Giả định").splitlines() if l.lstrip().startswith(("- ", "* "))]
    assert len(bullets) >= 3, "Ghi ít nhất ba giả định dạng gạch đầu dòng"


def test_time_log_within_box(submission):
    log = section(submission, "## Nhật ký thời gian")
    m = re.search(r"Tổng thời gian:\s*(\d+(?:[.,]\d+)?)\s*giờ", log)
    assert m, 'Nhật ký cần dòng "Tổng thời gian: X giờ"'
    assert float(m.group(1).replace(",", ".")) <= 3.5, "Take-home 3 giờ: tổng thời gian tối đa 3.5 giờ (kể cả dự phòng)"
