import re

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
COLUMNS = ["active", "new", "returning", "returning_share", "revenue", "returning_revenue_share"]
PLAN_HEADINGS = ["## Bối cảnh và quyết định", "## Câu hỏi đã đóng khung", "## Câu hỏi làm rõ gửi stakeholder",
                 "## Giả thuyết", "## Metric và định nghĩa", "## Dữ liệu và giới hạn", "## Phương pháp",
                 "## Đầu ra, thời hạn, ngoài phạm vi"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("baseline.ipynb")


def tiny_tx():
    # khách 1: mua tháng 1 và 3; khách 2: tháng 1 chỉ có đơn huỷ -> khách mới ở tháng 2; khách 3: mới tháng 3
    # một dòng không có Customer ID (bỏ), một dòng giá 0 (bỏ)
    return pd.DataFrame({
        "Invoice": [1, 1, "C2", 3, 4, 5, 6, 7, 8],
        "InvoiceDate": pd.to_datetime(["2011-01-05", "2011-01-05", "2011-01-20", "2011-02-03", "2011-02-28",
                                       "2011-03-01", "2011-03-15", "2011-03-20", "2011-03-21"]),
        "Quantity": [2, 3, -1, 4, 1, 5, 2, 9, 1],
        "Price": [10.0, 5.0, 8.0, 2.5, 4.0, 2.0, 20.0, 1.0, 0.0],
        "Customer ID": [1.0, 1.0, 2.0, 2.0, 2.0, 1.0, 3.0, np.nan, 3.0],
    })


def test_customer_baseline_new_and_returning(nb):
    tx = tiny_tx()
    before = tx.copy()
    out = nb.customer_baseline(tx)
    pd.testing.assert_frame_equal(tx, before)
    assert list(out.columns) == COLUMNS
    assert list(out.index) == list(pd.to_datetime(["2011-01-01", "2011-02-01", "2011-03-01"]))
    assert out.index.name == "month"
    assert out["active"].tolist() == [1, 1, 2]
    assert out["new"].tolist() == [1, 1, 1]
    assert out["returning"].tolist() == [0, 0, 1]
    assert out["returning_share"].tolist() == pytest.approx([0.0, 0.0, 0.5])
    # tháng 1: 20 + 15; tháng 2: 10 + 4; tháng 3: khách 1 = 10 (quay lại), khách 3 = 40 (mới)
    assert out["revenue"].tolist() == pytest.approx([35.0, 14.0, 50.0])
    assert out["returning_revenue_share"].tolist() == pytest.approx([0.0, 0.0, 0.2])


def test_customer_baseline_first_month_uses_given_data(nb):
    tx = tiny_tx()
    out = nb.customer_baseline(tx[tx["InvoiceDate"] >= "2011-03-01"])
    # cắt dữ liệu từ tháng 3: khách 1 bị đếm là "mới" (left-censoring)
    assert out["new"].tolist() == [2]
    assert out["returning"].tolist() == [0]


@pytest.fixture(scope="module")
def real_tx():
    path = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    return pd.read_excel(path, sheet_name="Year 2010-2011")      # xlsx: đọc một lần cho cả module


def test_real_baseline(nb, real_tx):
    out = nb.customer_baseline(real_tx)
    assert len(out) == 13
    dec10 = out.loc[pd.Timestamp("2010-12-01")]
    assert (dec10["active"], dec10["new"]) == (885, 885)
    nov11 = out.loc[pd.Timestamp("2011-11-01")]
    assert (nov11["active"], nov11["new"], nov11["returning"]) == (1664, 323, 1341)
    assert nov11["returning_revenue_share"] == pytest.approx(0.8824, abs=1e-4)
    assert out["revenue"].sum() == pytest.approx(8_911_425.90, abs=1)


def plan_text():
    return ex.read("ANALYSIS_PLAN.md")


def test_plan_has_no_todo_and_right_length():
    plan = plan_text()
    assert "TODO" not in plan, "Còn dòng TODO trong ANALYSIS_PLAN.md"
    words = len(plan.split())
    assert 300 <= words <= 900, f"Kế hoạch một trang: 300-900 từ, hiện có {words}"
    title = plan.strip().splitlines()[0]
    assert title.startswith("# "), "Dòng đầu là tiêu đề '# ...'"


def test_plan_sections_in_order():
    plan = plan_text()
    assert "TODO" not in plan, "Còn dòng TODO trong ANALYSIS_PLAN.md"
    positions = [plan.find(h) for h in PLAN_HEADINGS]
    missing = [h for h, p in zip(PLAN_HEADINGS, positions) if p < 0]
    assert not missing, f"Thiếu mục: {missing}"
    assert positions == sorted(positions), "Các mục phải theo đúng thứ tự của khung"


def test_plan_has_hypotheses_and_numbers():
    plan = plan_text()
    section = plan.split("## Giả thuyết", 1)[1].split("\n## ", 1)[0]
    bullets = [line for line in section.splitlines() if re.match(r"\s*[-*] ", line)]
    assert len(bullets) >= 3, "Mục Giả thuyết cần ít nhất 3 giả thuyết dạng gạch đầu dòng"
    data = plan.split("## Dữ liệu và giới hạn", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"\d", data), "Mục Dữ liệu và giới hạn cần nêu con số baseline đã tính"
