import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


def ts(values):
    return pd.to_datetime(values, format="ISO8601")


ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5", "o6", "o7"],
    "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6", "c7"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered", "delivered", "shipped"],
    "order_purchase_timestamp": ts([
        "2017-12-31 23:59:59", "2018-01-01 00:00:00", "2018-03-31 10:00:00", "2018-04-02",
        "2018-08-31 23:00:00", "2018-02-10", "2018-02-11"]),
    "order_delivered_customer_date": ts([
        "2018-01-05", "2018-01-09", "2018-04-10", None, "2018-09-10", None, None]),
})
REVIEWS = pd.DataFrame({
    "review_id": ["r1", "r2a", "r2b", "r3", "r4", "r5", "r6"],
    "order_id": ["o1", "o2", "o2", "o3", "o4", "o5", "o6"],
    "review_score": [5, 1, 4, 2, 1, 3, 1],
    "review_answer_timestamp": ts([
        "2018-01-06", "2018-01-10", "2018-01-12", "2018-04-11", "2018-04-12", "2018-09-11", "2018-02-20"]),
})


@pytest.fixture(scope="module")
def labels():
    return ex.module("labels.py")


def test_label_keeps_delivered_orders_with_review(labels):
    out = labels.label_orders(ORDERS, REVIEWS)
    # o4 huỷ, o6 không có ngày giao, o7 chưa giao: loại
    assert sorted(out.order_id) == ["o1", "o2", "o3", "o5"]
    assert out.order_id.is_unique


def test_label_uses_latest_review(labels):
    out = labels.label_orders(ORDERS, REVIEWS).set_index("order_id")
    # o2 có hai review: review trả lời sau cùng là 4 sao
    assert out.loc["o2", "review_score"] == 4
    assert out.loc["o2", "bad_review"] == 0
    assert out.loc["o3", "bad_review"] == 1          # 2 sao là review xấu
    assert out.loc["o5", "bad_review"] == 0          # 3 sao không phải
    assert set(out.bad_review.unique()) <= {0, 1}
    assert "customer_id" in out.columns and "order_purchase_timestamp" in out.columns


def test_label_does_not_mutate_inputs(labels):
    orders, reviews = ORDERS.copy(), REVIEWS.copy()
    labels.label_orders(orders, reviews)
    pd.testing.assert_frame_equal(orders, ORDERS)
    pd.testing.assert_frame_equal(reviews, REVIEWS)


def test_time_split_boundaries(labels):
    df = pd.DataFrame({"order_purchase_timestamp": ts([
        "2016-10-04", "2017-12-31 23:59:59", "2018-01-01 00:00:00", "2018-03-31 23:59:59",
        "2018-04-01 00:00:00", "2018-08-31 23:59:59", "2018-09-01 00:00:00", "2018-10-17"]),
        "bad_review": [0, 1, 0, 1, 1, 0, 1, 1]})
    out = labels.time_split(df)
    assert set(out) == {"train", "val", "test"}
    assert list(out["train"].index) == [0, 1]
    assert list(out["val"].index) == [2, 3]
    assert list(out["test"].index) == [4, 5]   # đơn từ 2018-09-01 bị bỏ


def test_time_split_custom_column_and_unsorted(labels):
    df = pd.DataFrame({"t": ts(["2018-05-01", "2017-01-01", "2018-02-01"]), "x": [1, 2, 3]})
    out = labels.time_split(df, date_col="t")
    assert out["train"].x.tolist() == [2]
    assert out["val"].x.tolist() == [3]
    assert out["test"].x.tolist() == [1]


def test_split_summary(labels):
    df = pd.DataFrame({"order_purchase_timestamp": ts([
        "2017-03-01", "2017-06-01", "2018-02-01", "2018-05-01", "2018-06-01", "2018-07-01"]),
        "bad_review": [0, 1, 1, 0, 0, 1]})
    out = labels.split_summary(labels.time_split(df))
    assert list(out.index) == ["train", "val", "test"]
    assert out.loc["train", "n"] == 2 and out.loc["test", "n"] == 3
    assert out.loc["train", "bad_rate"] == pytest.approx(0.5)
    assert out.loc["test", "bad_rate"] == pytest.approx(1 / 3)
    assert out.loc["test", "start"] == pd.Timestamp("2018-05-01")
    assert out.loc["test", "end"] == pd.Timestamp("2018-07-01")


def test_real_olist(labels):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv",
                         parse_dates=["order_purchase_timestamp", "order_delivered_customer_date"])
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    out = labels.label_orders(orders, reviews)
    assert len(out) == 95824
    assert out.bad_review.mean() == pytest.approx(0.128, abs=0.001)
    summary = labels.split_summary(labels.time_split(out))
    assert summary.n.tolist() == [43362, 20468, 31994]
    assert summary.bad_rate.tolist() == pytest.approx([0.1213, 0.1804, 0.1038], abs=5e-4)
