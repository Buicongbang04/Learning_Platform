import warnings

import numpy as np
import pandas as pd
import pytest

with warnings.catch_warnings():
    # Starlette mới khuyên dùng gói httpx2; httpx vẫn chạy đúng, chỉ tắt dòng cảnh báo này
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from testkit import Exercise

ex = Exercise(__file__)

NUMERIC = ["promised_days", "delivery_days", "delay_days", "approve_hours", "n_items", "n_sellers",
           "price", "freight", "freight_ratio", "payment_installments"]
CATEGORICAL = ["customer_state", "payment_type"]


def make_orders(n: int, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    promised = rng.uniform(10, 40, n)
    delivery = np.clip(promised + rng.normal(-10, 8, n), 1, None)
    price = rng.lognormal(4.5, 0.8, n)
    freight = rng.lognormal(2.8, 0.5, n)
    return pd.DataFrame({
        "order_id": [f"o{i}" for i in range(n)],
        "promised_days": promised, "delivery_days": delivery, "delay_days": delivery - promised,
        "approve_hours": rng.exponential(10, n), "n_items": rng.integers(1, 4, n),
        "n_sellers": np.ones(n, dtype=int), "price": price, "freight": freight,
        "freight_ratio": freight / (price + freight), "payment_installments": rng.integers(1, 10, n).astype(float),
        "customer_state": rng.choice(["SP", "RJ", "MG", "BA"], n),
        "payment_type": rng.choice(["credit_card", "boleto", "voucher"], n),
    })


@pytest.fixture(scope="module")
def pipeline():
    df = make_orders(600, seed=1)
    y = (df.delay_days + np.random.default_rng(2).normal(0, 4, len(df)) > 0).astype(int)
    pre = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])
    return make_pipeline(pre, LogisticRegression(max_iter=1000)).fit(df[NUMERIC + CATEGORICAL], y)


class SpyModel:
    """Model giả: ghi lại mỗi lần được gọi, score = sigmoid(delay_days)."""

    def __init__(self):
        self.calls = []

    def predict_proba(self, X):
        self.calls.append(X.copy())
        s = 1 / (1 + np.exp(-X["delay_days"].to_numpy(dtype=float)))
        return np.column_stack([1 - s, s])


@pytest.fixture(scope="module")
def service():
    return ex.module("service.py")


def payload(df: pd.DataFrame) -> dict:
    return {"orders": df.to_dict(orient="records")}


def test_health(service, pipeline):
    client = TestClient(service.create_app(pipeline, model_version="7"))
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_version": "7"}


def test_predict_matches_model(service, pipeline):
    df = make_orders(25, seed=3)
    client = TestClient(service.create_app(pipeline, model_version="3", threshold=0.5))
    r = client.post("/predict", json=payload(df))
    assert r.status_code == 200
    body = r.json()
    assert body["model_version"] == "3"
    want = pipeline.predict_proba(df[NUMERIC + CATEGORICAL])[:, 1]
    got = [p["score"] for p in body["predictions"]]
    assert [p["order_id"] for p in body["predictions"]] == df.order_id.tolist()
    assert got == pytest.approx(want, abs=1e-9)
    assert [p["high_risk"] for p in body["predictions"]] == (want >= 0.5).tolist()


def test_threshold_is_configurable(service):
    df = make_orders(3, seed=4).assign(delay_days=[-3.0, 0.5, 4.0])
    client = TestClient(service.create_app(SpyModel(), model_version="1", threshold=0.7))
    flags = [p["high_risk"] for p in client.post("/predict", json=payload(df)).json()["predictions"]]
    assert flags == [False, False, True]          # sigmoid: 0.047, 0.622, 0.982


def test_model_called_once_per_request_with_feature_columns(service):
    spy = SpyModel()
    client = TestClient(service.create_app(spy, model_version="1"))
    client.post("/predict", json=payload(make_orders(40, seed=5)))
    assert len(spy.calls) == 1                      # cả batch một lần, không lặp từng dòng
    X = spy.calls[0]
    assert isinstance(X, pd.DataFrame) and len(X) == 40
    assert list(X.columns) == NUMERIC + CATEGORICAL  # đúng tên, đúng thứ tự, không có order_id


def test_null_optional_fields_become_nan(service, pipeline):
    df = make_orders(2, seed=6)
    body = payload(df)
    body["orders"][0]["approve_hours"] = None        # đơn chưa duyệt, như 14 đơn trong Olist
    spy = SpyModel()
    r = TestClient(service.create_app(spy, model_version="1")).post("/predict", json=body)
    assert r.status_code == 200
    assert np.isnan(spy.calls[0]["approve_hours"].iloc[0])
    r = TestClient(service.create_app(pipeline, model_version="1")).post("/predict", json=body)
    assert r.status_code == 200 and 0 <= r.json()["predictions"][0]["score"] <= 1


@pytest.mark.parametrize("field, value", [
    ("price", -10.0),
    ("n_items", 0),
    ("freight_ratio", 1.5),
    ("payment_type", "bitcoin"),
    ("customer_state", "Sao Paulo"),
])
def test_invalid_input_rejected_before_model(service, field, value):
    spy = SpyModel()
    body = payload(make_orders(2, seed=7))
    body["orders"][1][field] = value
    r = TestClient(service.create_app(spy, model_version="1")).post("/predict", json=body)
    assert r.status_code == 422
    assert spy.calls == []


def test_missing_field_and_batch_limits(service):
    spy = SpyModel()
    client = TestClient(service.create_app(spy, model_version="1"))
    body = payload(make_orders(1, seed=8))
    del body["orders"][0]["delay_days"]
    assert client.post("/predict", json=body).status_code == 422
    assert client.post("/predict", json={"orders": []}).status_code == 422
    assert client.post("/predict", json=payload(make_orders(1001, seed=9))).status_code == 422
    assert client.post("/predict", json=payload(make_orders(1000, seed=9))).status_code == 200
