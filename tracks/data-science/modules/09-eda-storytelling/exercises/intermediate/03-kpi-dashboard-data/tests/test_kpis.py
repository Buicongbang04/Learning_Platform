import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)
RAW = ROOT / "data" / "raw"
COLUMNS = ["orders", "delivered", "late_rate", "bad_review_rate", "complete"]


@pytest.fixture(scope="module")
def kpis():
    return ex.module("kpis.py")


def ts(values):
    return pd.to_datetime(pd.Series(values, dtype="object"), format="ISO8601")


# Tháng 2 không có đơn nào; tháng 4 chỉ có một đơn chưa giao
ORDERS = pd.DataFrame({
    "order_id": ["a1", "a2", "a3", "a4", "c1", "c2", "c3", "d1"],
    "order_status": ["delivered", "delivered", "delivered", "canceled",
                     "delivered", "delivered", "delivered", "shipped"],
    "order_purchase_timestamp": ts(["2018-01-03", "2018-01-10", "2018-01-20", "2018-01-25",
                                    "2018-03-02", "2018-03-05", "2018-03-30", "2018-04-02 09:00"]),
    "order_delivered_customer_date": ts(["2018-01-10", "2018-01-30 15:00", "2018-01-28", None,
                                         "2018-03-12", None, "2018-04-20", None]),
    "order_estimated_delivery_date": ts(["2018-01-20", "2018-01-30", "2018-02-05", "2018-02-05",
                                         "2018-03-20", "2018-03-25", "2018-04-15", "2018-04-25"]),
})
REVIEWS = pd.DataFrame({
    "order_id": ["a1", "a2", "a2", "c1", "c3"],
    "review_score": [5, 4, 1, 2, 5],
    "review_answer_timestamp": ts(["2018-01-11", "2018-02-01", "2018-02-03", "2018-03-13", "2018-04-21"]),
})


def test_grid_includes_empty_month(kpis):
    out = kpis.monthly_kpis(ORDERS, REVIEWS)
    assert list(out.columns) == COLUMNS
    assert [str(p) for p in out.index] == ["2018-01", "2018-02", "2018-03", "2018-04"]
    assert isinstance(out.index, pd.PeriodIndex)
    assert out.loc[pd.Period("2018-02", "M"), "orders"] == 0
    assert np.isnan(out.loc[pd.Period("2018-02", "M"), "late_rate"])


def test_counts_and_rates(kpis):
    out = kpis.monthly_kpis(ORDERS, REVIEWS)
    jan, mar = pd.Period("2018-01", "M"), pd.Period("2018-03", "M")
    assert out.loc[jan, "orders"] == 4 and out.loc[jan, "delivered"] == 3
    assert out.loc[jan, "late_rate"] == pytest.approx(1 / 3)          # a2 giao 15:00 đúng ngày hẹn: trễ
    assert out.loc[jan, "bad_review_rate"] == pytest.approx(1 / 2)    # a1: 5 sao; a2: review mới nhất 1 sao; a3 không review
    assert out.loc[mar, "delivered"] == 2                              # c2 thiếu ngày giao
    assert out.loc[mar, "late_rate"] == pytest.approx(1 / 2)
    assert out.loc[mar, "bad_review_rate"] == pytest.approx(1 / 2)
    apr = pd.Period("2018-04", "M")
    assert out.loc[apr, "orders"] == 1 and out.loc[apr, "delivered"] == 0


def test_complete_flag_default_snapshot(kpis):
    # snapshot mặc định = 2018-04-02 09:00; cuối tháng + 30 ngày phải <= snapshot
    # tháng 2: 28/2 23:59 + 30 ngày = 30/3 23:59 → đã chín; tháng 3: 30/4 → chưa
    out = kpis.monthly_kpis(ORDERS, REVIEWS)
    assert out.complete.tolist() == [True, True, False, False]
    assert out.complete.dtype == bool


def test_complete_flag_custom(kpis):
    out = kpis.monthly_kpis(ORDERS, REVIEWS, snapshot=pd.Timestamp("2018-05-01"), maturity_days=0)
    assert out.complete.tolist() == [True, True, True, True]
    out = kpis.monthly_kpis(ORDERS, REVIEWS, snapshot=pd.Timestamp("2018-05-01"), maturity_days=30)
    assert out.complete.tolist() == [True, True, True, False]       # 31/3 + 30 ngày = 30/4 23:59 <= 1/5


def test_latest_complete(kpis):
    out = kpis.monthly_kpis(ORDERS, REVIEWS, snapshot=pd.Timestamp("2018-05-01"))
    assert kpis.latest_complete(out) == pd.Period("2018-03", "M")


def test_headline_rate(kpis):
    assert kpis.headline("Tỉ lệ giao trễ", 0.061, 0.094) == "Tỉ lệ giao trễ tăng từ 6.1% lên 9.4% (+3.3 điểm %)"
    assert kpis.headline("Tỉ lệ review xấu", 0.212, 0.118) == "Tỉ lệ review xấu giảm từ 21.2% xuống 11.8% (-9.4 điểm %)"
    assert kpis.headline("Tỉ lệ trễ", 0.0801, 0.0803) == "Tỉ lệ trễ không đổi ở 8.0%"


def test_headline_count(kpis):
    assert kpis.headline("Số đơn", 6292, 6512, kind="count") == "Số đơn tăng 3% (từ 6 292 lên 6 512)"
    assert kpis.headline("Số đơn", 7211, 6939, kind="count") == "Số đơn giảm 4% (từ 7 211 xuống 6 939)"
    assert kpis.headline("Số đơn", 1000, 1001, kind="count") == "Số đơn không đổi ở 1 001"


def test_headline_invalid_kind(kpis):
    with pytest.raises(ValueError):
        kpis.headline("x", 1, 2, kind="ratio")


def test_kpi_headline_skips_incomplete_month(kpis):
    out = kpis.monthly_kpis(ORDERS, REVIEWS, snapshot=pd.Timestamp("2018-05-01"))
    # tháng complete mới nhất là 3 (so với tháng 2, 0 đơn); tháng 4 dở dang bị bỏ qua
    assert kpis.kpi_headline(out, "late_rate", "Tỉ lệ giao trễ").startswith("Tỉ lệ giao trễ")
    text = kpis.kpi_headline(out.assign(late_rate=[0.2, 0.25, 0.3, 0.9]), "late_rate", "Trễ")
    assert text == "Trễ tăng từ 25.0% lên 30.0% (+5.0 điểm %)"


def test_real_olist(kpis):
    if not (RAW / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=dates)
    reviews = pd.read_csv(RAW / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    out = kpis.monthly_kpis(orders, reviews)
    assert len(out) == 26                                             # 2016-09 … 2018-10, kể cả 2016-11
    assert out.loc[pd.Period("2016-11", "M"), "orders"] == 0
    assert out.loc[pd.Period("2018-09", "M"), "orders"] == 16
    assert out.orders.sum() == 99441 and out.delivered.sum() == 96470
    assert out.loc[pd.Period("2018-03", "M"), "late_rate"] == pytest.approx(0.2136, abs=5e-4)
    assert out.loc[pd.Period("2018-03", "M"), "bad_review_rate"] == pytest.approx(0.2117, abs=5e-4)
    assert kpis.latest_complete(out) == pd.Period("2018-08", "M")
    assert kpis.kpi_headline(out, "orders", "Số đơn", "count") == "Số đơn tăng 3% (từ 6 292 lên 6 512)"
    assert kpis.kpi_headline(out, "late_rate", "Tỉ lệ giao trễ") == "Tỉ lệ giao trễ tăng từ 4.5% lên 10.4% (+5.9 điểm %)"
