import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)

SNAPSHOT = pd.Timestamp("2018-09-01")

ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5", "o6", "o7"],
    "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6", "c7"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered", "delivered", "delivered"],
    "order_purchase_timestamp": pd.to_datetime([
        "2018-08-01 10:00", "2018-06-01 09:00", "2018-08-21 23:00", "2018-08-25 10:00",
        "2018-03-10 08:00", "2018-09-02 08:00", "2018-07-01 12:00"]),
    "order_delivered_customer_date": pd.to_datetime([
        "2018-08-05", "2018-06-05", "2018-08-28", None, "2018-03-15", "2018-09-04", "2018-07-09"]),
})
# c1 và c2 là cùng một người (customer_unique_id u1): Olist cấp customer_id mới cho mỗi đơn
CUSTOMERS = pd.DataFrame({
    "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6", "c7"],
    "customer_unique_id": ["u1", "u1", "u2", "u3", "u4", "u5", "u6"],
})
PAYMENTS = pd.DataFrame({
    "order_id": ["o1", "o1", "o2", "o3", "o4", "o5", "o6"],
    "payment_value": [50.0, 30.0, 20.0, 200.0, 99.0, 10.0, 5.0],
})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("rfm.ipynb")


def test_rfm_table_values(nb):
    rfm = nb.rfm_table(ORDERS, CUSTOMERS, PAYMENTS, SNAPSHOT)
    # u3 chỉ có đơn huỷ; u5 mua sau snapshot; u6 có đơn giao xong nhưng không có payment
    assert sorted(rfm.index) == ["u1", "u2", "u4", "u6"]
    assert list(rfm.columns[:3]) == ["recency", "frequency", "monetary"]
    assert rfm.loc["u1", "frequency"] == 2
    assert rfm.loc["u1", "monetary"] == pytest.approx(100.0)
    assert rfm.loc["u1", "recency"] == 30            # 2018-08-01 10:00 tới 2018-09-01: 30 ngày trọn
    assert rfm.loc["u2", "recency"] == 10
    assert rfm.loc["u4", "monetary"] == pytest.approx(10.0)
    assert rfm.loc["u6", "monetary"] == 0 and rfm.loc["u6", "frequency"] == 1


def test_prepare_features(nb):
    rfm = pd.DataFrame({"recency": [1, 10, 100, 300], "frequency": [1, 1, 2, 5],
                        "monetary": [10.0, 100.0, 1000.0, 50.0]}, index=list("abcd"))
    X = nb.prepare_features(rfm)
    assert X.shape == (4, 3)
    np.testing.assert_allclose(X.mean(axis=0), 0, atol=1e-9)
    np.testing.assert_allclose(X.std(axis=0), 1, atol=1e-9)
    # log trước khi chuẩn hoá: khoảng cách 10 -> 100 bằng 100 -> 1000 trên trục monetary
    assert X[1, 2] - X[0, 2] == pytest.approx(X[2, 2] - X[1, 2], rel=0.05)


def test_fit_kmeans_recovers_blobs(nb):
    X, truth = make_blobs(600, centers=4, cluster_std=0.6, random_state=0)
    labels = nb.fit_kmeans(X, 4, seed=0)
    assert len(labels) == 600 and len(set(labels)) == 4
    assert adjusted_rand_score(truth, labels) > 0.95
    np.testing.assert_array_equal(labels, nb.fit_kmeans(X, 4, seed=0))


def test_silhouette_by_k_finds_three(nb):
    X, _ = make_blobs(900, centers=3, cluster_std=0.5, random_state=1)
    scores = nb.silhouette_by_k(X, [2, 3, 4, 5], seed=0)
    assert list(scores.index) == [2, 3, 4, 5]
    assert scores.idxmax() == 3
    assert scores.between(-1, 1).all()


def test_segment_profile(nb):
    rfm = pd.DataFrame({"recency": [10, 20, 300, 400, 500], "frequency": [2, 4, 1, 1, 1],
                        "monetary": [100.0, 300.0, 50.0, 60.0, 70.0]}, index=list("abcde"))
    prof = nb.segment_profile(rfm, np.array([1, 1, 0, 0, 0]))
    assert list(prof.index) == [0, 1]
    assert {"n", "share", "recency_median", "frequency_mean", "repeat_rate", "monetary_median"} <= set(prof.columns)
    assert prof.loc[0, "n"] == 3 and prof.loc[1, "share"] == pytest.approx(0.4)
    assert prof.loc[1, "recency_median"] == pytest.approx(15)
    assert prof.loc[1, "frequency_mean"] == pytest.approx(3)
    assert prof.loc[0, "repeat_rate"] == 0 and prof.loc[1, "repeat_rate"] == 1
    assert prof.loc[0, "monetary_median"] == pytest.approx(60)


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv",
                         parse_dates=["order_purchase_timestamp", "order_delivered_customer_date"])
    customers = pd.read_csv(raw / "olist_customers_dataset.csv")
    payments = pd.read_csv(raw / "olist_order_payments_dataset.csv")
    rfm = nb.rfm_table(orders, customers, payments, SNAPSHOT)
    assert len(rfm) == 93350
    assert (rfm.frequency > 1).mean() == pytest.approx(0.030, abs=0.001)
    assert rfm.monetary.median() == pytest.approx(107.8, abs=0.5)
