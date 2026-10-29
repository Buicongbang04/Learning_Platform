import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5", "o6", "o7"],
    "order_status": ["delivered", "delivered", "delivered", "delivered", "canceled", "delivered", "delivered"],
    "order_purchase_timestamp": pd.to_datetime([
        "2018-01-01", "2018-01-03", "2018-01-09", "2018-01-10", "2018-01-11", "2018-01-16", "2018-01-24"]),
    "order_delivered_customer_date": pd.to_datetime([
        "2018-01-08", "2018-01-20", "2018-01-15", "2018-01-30", None, None, "2018-01-29"]),
    "order_estimated_delivery_date": pd.to_datetime([
        "2018-01-10", "2018-01-15", "2018-01-20", "2018-01-25", "2018-01-30", "2018-01-30", "2018-02-05"]),
})
REVIEWS = pd.DataFrame({
    "review_id": ["r1", "r2", "r2b", "r3", "r4", "r5"],
    "order_id": ["o1", "o2", "o2", "o3", "o4", "o5"],
    "review_score": [5, 4, 1, 2, 1, 1],
    "review_answer_timestamp": pd.to_datetime([
        "2018-01-09", "2018-01-21", "2018-01-25", "2018-01-16", "2018-02-01", "2018-01-12"]),
})


@pytest.fixture(scope="module")
def design():
    return ex.module("design.py")


def test_baseline_keys(design):
    out = design.baseline(ORDERS, REVIEWS)
    assert set(out) == {"bad_review_rate", "late_rate", "bad_review_rate_late", "delivered_per_week"}


def test_baseline_values(design):
    out = design.baseline(ORDERS, REVIEWS)
    # đơn giao xong có ngày giao: o1, o2, o3, o4, o7; có review: o1, o2 (lấy review mới nhất: 1 sao), o3, o4
    assert out["bad_review_rate"] == pytest.approx(3 / 4)
    # trễ: o2, o4 trên 5 đơn giao xong
    assert out["late_rate"] == pytest.approx(2 / 5)
    assert out["bad_review_rate_late"] == pytest.approx(1.0)
    # tuần mua (kết thúc Chủ nhật): 01-07: 2 đơn | 08-14: 2 | 15-21: 0 | 22-28: 1 → bỏ tuần đầu, tuần cuối
    assert out["delivered_per_week"] == pytest.approx(1.0)


def test_real_olist(design):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    out = design.baseline(orders, reviews)
    assert out["bad_review_rate"] == pytest.approx(0.128, abs=0.005)
    assert out["late_rate"] == pytest.approx(0.081, abs=0.005)
    assert out["bad_review_rate_late"] > 0.5


def test_design_doc_written():
    doc = ex.read("DESIGN.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 400
