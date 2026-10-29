import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def leak():
    return ex.module("leak_check.py")


def make_data(seed: int, n: int = 3000):
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=n)
    y = (rng.random(n) < 1 / (1 + np.exp(-signal))).astype(int)
    X = pd.DataFrame({
        "noise": rng.normal(size=n),
        "weak": signal + rng.normal(scale=2, size=n),
        "leak": y + rng.normal(scale=0.05, size=n),        # gần như bản sao của nhãn
        "leak_negative": -y * 3 + rng.normal(scale=0.1, size=n),
    })
    return X, y


def test_single_feature_auc_values(leak):
    X, y = make_data(0)
    out = leak.single_feature_auc(X, y)
    assert set(out.index) == set(X.columns)
    assert out["weak"] == pytest.approx(roc_auc_score(y, X["weak"]))
    assert out["leak_negative"] == pytest.approx(1 - roc_auc_score(y, X["leak_negative"]))
    assert out["leak_negative"] > 0.99
    assert 0.45 < out["noise"] < 0.55
    assert list(out.values) == sorted(out.values, reverse=True)


def test_nan_and_constant_columns(leak):
    y = np.array([0, 1, 0, 1, 1, 0])
    X = pd.DataFrame({"with_nan": [0.1, 0.9, np.nan, 0.8, np.nan, 0.2],
                      "constant": [1.0] * 6,
                      "one_class_left": [np.nan, 1.0, np.nan, 2.0, 3.0, np.nan]})
    out = leak.single_feature_auc(X, y)
    assert out["with_nan"] == pytest.approx(1.0)
    assert out["constant"] == pytest.approx(0.5)
    assert out["one_class_left"] == pytest.approx(0.5)


def test_suspicious_features(leak):
    X, y = make_data(1)
    assert set(leak.suspicious_features(X, y)) == {"leak", "leak_negative"}
    assert "weak" not in leak.suspicious_features(X, y, threshold=0.75)
    loose = leak.suspicious_features(X, y, threshold=0.55)
    assert set(loose[:2]) == {"leak", "leak_negative"} and loose[2:] == ["weak"]


def test_available_after(leak):
    df = pd.DataFrame({
        "delivered": pd.to_datetime(["2018-01-10", "2018-01-10", "2018-01-10", None]),
        "purchase": pd.to_datetime(["2018-01-01", "2018-01-02", "2018-01-03", "2018-01-04"]),
        "review_answer": pd.to_datetime(["2018-01-12", "2018-01-09", "2018-01-10", "2018-01-11"]),
        "estimated": pd.to_datetime(["2018-01-20", "2018-01-20", "2018-01-05", "2018-01-20"]),
    })
    out = leak.available_after(df, {"review_score": "review_answer", "estimated": "purchase"}, "delivered")
    assert out["review_score"] == pytest.approx(1 / 3)      # bằng nhau thì không tính; dòng thiếu mốc bị bỏ
    assert out["estimated"] == pytest.approx(0.0)            # giá trị là ngày tương lai nhưng biết từ lúc mua


def test_real_olist(leak):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=[
        "order_purchase_timestamp", "order_approved_at", "order_delivered_customer_date",
        "order_estimated_delivery_date"])
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv",
                          parse_dates=["review_creation_date", "review_answer_timestamp"])
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    df = delivered.merge(latest, on="order_id")
    known_at = {"review_score": "review_answer_timestamp", "review_comment_message": "review_creation_date",
                "order_estimated_delivery_date": "order_purchase_timestamp", "order_approved_at": "order_approved_at"}
    after = leak.available_after(df, known_at, "order_delivered_customer_date")
    assert after["review_score"] == pytest.approx(0.9514, abs=5e-4)
    assert after["review_comment_message"] == pytest.approx(0.9151, abs=5e-4)
    assert after["order_estimated_delivery_date"] == 0
    assert after["order_approved_at"] < 0.001
    y = (df.review_score <= 2).astype(int)
    X = pd.DataFrame({
        "delay_days": (df.order_delivered_customer_date - df.order_estimated_delivery_date) / pd.Timedelta(days=1),
        "comment_len": df.review_comment_message.fillna("").str.len(),
    })
    auc = leak.single_feature_auc(X, y)
    assert auc["comment_len"] == pytest.approx(0.756, abs=0.002)
    assert auc["delay_days"] == pytest.approx(0.657, abs=0.002)
