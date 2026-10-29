import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from testkit import ROOT, Exercise

ex = Exercise(__file__)

FEATURES = ["delivery_days", "late_days", "estimated_days", "n_items", "n_sellers",
            "total_price", "freight_ratio", "max_installments"]



def dt(values):
    return pd.to_datetime(values, format="mixed")


ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5", "o6", "o7"],
    "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6", "c7"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered", "delivered", "delivered"],
    "order_purchase_timestamp": dt([
        "2017-12-31 23:00", "2018-01-01 00:00", "2018-04-02 10:00", "2018-02-01", "2018-03-01",
        "2018-09-01 00:00", "2018-05-05"]),
    "order_delivered_customer_date": dt([
        "2018-01-10 23:00", "2018-01-20 12:00", "2018-04-10 10:00", None, None, "2018-09-05", "2018-05-15"]),
    "order_estimated_delivery_date": dt([
        "2018-01-15", "2018-01-15", "2018-04-20", "2018-02-20", "2018-03-20", "2018-09-20", "2018-05-30"]),
})
REVIEWS = pd.DataFrame({
    "review_id": ["r1", "r2a", "r2b", "r3", "r4", "r6"],
    "order_id": ["o1", "o2", "o2", "o3", "o4", "o6"],
    "review_score": [5, 1, 4, 2, 1, 1],
    "review_answer_timestamp": dt([
        "2018-01-12", "2018-01-22", "2018-01-21", "2018-04-12", "2018-02-02", "2018-09-06"]),
})
ITEMS = pd.DataFrame({
    "order_id": ["o1", "o1", "o2", "o3", "o4", "o6", "o7"],
    "order_item_id": [1, 2, 1, 1, 1, 1, 1],
    "seller_id": ["s1", "s2", "s1", "s3", "s1", "s1", "s1"],
    "price": [60.0, 20.0, 100.0, 50.0, 10.0, 10.0, 10.0],
    "freight_value": [10.0, 10.0, 25.0, 0.0, 5.0, 5.0, 5.0],
})
PAYMENTS = pd.DataFrame({
    "order_id": ["o1", "o1", "o3", "o4", "o6", "o7"],
    "payment_sequential": [1, 2, 1, 1, 1, 1],
    "payment_installments": [3, 1, 6, 1, 1, 1],
    "payment_value": [80.0, 20.0, 50.0, 15.0, 15.0, 15.0],
})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("models.ipynb")


def synthetic(n: int, seed: int, start: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.normal(size=n) for c in FEATURES})
    logit = -2 + 1.8 * df.late_days + 0.6 * df.delivery_days
    df["bad_review"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    df["order_purchase_timestamp"] = pd.Timestamp(start) + pd.to_timedelta(rng.integers(0, 80, n), unit="D")
    return df


def test_build_dataset_rows(nb):
    out = nb.build_dataset(ORDERS, REVIEWS, ITEMS, PAYMENTS).set_index("order_id")
    # o4 huỷ, o5 chưa giao, o6 mua sau 2018-08-31, o7 không có review
    assert sorted(out.index) == ["o1", "o2", "o3"]
    assert {"order_purchase_timestamp", "bad_review", *FEATURES} <= set(out.columns)


def test_build_dataset_values(nb):
    out = nb.build_dataset(ORDERS, REVIEWS, ITEMS, PAYMENTS).set_index("order_id")
    assert out.loc["o2", "bad_review"] == 1                 # review mới nhất (1 sao) thắng
    assert out.loc["o1", "bad_review"] == 0 and out.loc["o3", "bad_review"] == 1
    assert out.loc["o1", "delivery_days"] == pytest.approx(10.0)
    assert out.loc["o1", "late_days"] == pytest.approx(-(4 + 1 / 24))
    assert out.loc["o2", "late_days"] == pytest.approx(5.5)
    assert out.loc["o1", "estimated_days"] == pytest.approx(14 + 1 / 24)
    assert out.loc["o1", "n_items"] == 2 and out.loc["o1", "n_sellers"] == 2
    assert out.loc["o1", "total_price"] == pytest.approx(80.0)
    assert out.loc["o1", "freight_ratio"] == pytest.approx(20 / 100)
    assert out.loc["o1", "max_installments"] == 3
    assert out.loc["o2", "max_installments"] == 1           # không có payment: coi như trả 1 lần


def test_time_split_boundaries(nb):
    df = pd.DataFrame({"order_purchase_timestamp": dt([
        "2017-12-31 23:59", "2018-01-01 00:00", "2018-03-31 23:59", "2018-04-01 00:00",
        "2018-08-31 23:59", "2018-09-01 00:00"]), "x": range(6)})
    train, val, test = nb.time_split(df)
    assert train.x.tolist() == [0] and val.x.tolist() == [1, 2] and test.x.tolist() == [3, 4]


def test_evaluate_matches_sklearn(nb):
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    p = np.clip(0.4 * y + 0.6 * rng.random(500), 0.01, 0.99)
    out = nb.evaluate(y, p)
    assert set(out) == {"roc_auc", "pr_auc", "log_loss", "brier"}
    assert out["roc_auc"] == pytest.approx(roc_auc_score(y, p))
    assert out["pr_auc"] == pytest.approx(average_precision_score(y, p))
    assert out["brier"] == pytest.approx(np.mean((p - y) ** 2))
    assert out["log_loss"] == pytest.approx(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def test_compare_models_detects_overfitting(nb):
    train, val = synthetic(3000, 1, "2017-06-01"), synthetic(2000, 2, "2018-01-01")
    models = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "tree_full": DecisionTreeClassifier(random_state=0),
    }
    table = nb.compare_models(models, train, val)
    assert set(table.index) == {"logistic", "tree_full"}
    assert {"roc_auc", "pr_auc", "log_loss", "brier", "train_roc_auc"} <= set(table.columns)
    assert table.index[0] == "logistic"                     # sắp theo pr_auc giảm dần
    assert table.pr_auc.is_monotonic_decreasing
    assert table.loc["tree_full", "train_roc_auc"] > 0.99
    assert table.loc["tree_full", "roc_auc"] < table.loc["tree_full", "train_roc_auc"] - 0.15
    assert table.loc["logistic", "roc_auc"] > 0.8


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    payments = pd.read_csv(raw / "olist_order_payments_dataset.csv")
    df = nb.build_dataset(orders, reviews, items, payments)
    assert len(df) == 95824
    assert df.bad_review.mean() == pytest.approx(0.128, abs=0.002)
    train, val, test = nb.time_split(df)
    assert (len(train), len(val), len(test)) == (43362, 20468, 31994)
    assert val.bad_review.mean() == pytest.approx(0.180, abs=0.002)
