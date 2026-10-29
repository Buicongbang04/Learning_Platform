import json

import numpy as np
import pandas as pd
import pytest
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
FEATURES = NUMERIC + CATEGORICAL
TS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_customer_date",
      "order_estimated_delivery_date"]


def make_raw(n: int, seed: int) -> pd.DataFrame:
    """Đơn thô như trong bảng orders + items + payments, mỗi đơn một dòng."""
    rng = np.random.default_rng(seed)
    purchase = pd.Timestamp("2018-03-01") + pd.to_timedelta(rng.integers(0, 60 * 86400, n), unit="s")
    approved = purchase + pd.to_timedelta(rng.integers(60, 3 * 86400, n), unit="s")
    approved = pd.Series(approved).mask(rng.random(n) < 0.1)                  # có đơn chưa từng duyệt
    estimated = (purchase + pd.to_timedelta(rng.integers(10, 40, n), unit="D")).normalize()
    delivered = purchase + pd.to_timedelta(rng.integers(2 * 86400, 45 * 86400, n), unit="s")
    price = np.round(rng.lognormal(4.5, 0.8, n), 2)
    freight = np.round(rng.lognormal(2.8, 0.5, n), 2)
    return pd.DataFrame({
        "order_id": [f"o{seed}-{i}" for i in range(n)],
        "order_purchase_timestamp": purchase, "order_approved_at": approved.to_numpy(),
        "order_delivered_customer_date": delivered, "order_estimated_delivery_date": estimated,
        "n_items": rng.integers(1, 4, n), "n_sellers": np.ones(n, dtype=int),
        "price": price, "freight": freight,
        "payment_type": pd.Series(rng.choice(["credit_card", "boleto", "voucher"], n)).mask(rng.random(n) < 0.05).to_numpy(),
        "payment_installments": pd.Series(rng.integers(1, 10, n).astype(float)).mask(rng.random(n) < 0.05).to_numpy(),
        "customer_state": rng.choice(["SP", "RJ", "MG", "BA"], n),
    })


def reference_features(raw: pd.DataFrame) -> pd.DataFrame:
    day = pd.Timedelta(days=1)
    out = pd.DataFrame({
        "promised_days": (raw.order_estimated_delivery_date - raw.order_purchase_timestamp) / day,
        "delivery_days": (raw.order_delivered_customer_date - raw.order_purchase_timestamp) / day,
        "delay_days": (raw.order_delivered_customer_date - raw.order_estimated_delivery_date) / day,
        "approve_hours": (raw.order_approved_at - raw.order_purchase_timestamp) / pd.Timedelta(hours=1),
        "n_items": raw.n_items, "n_sellers": raw.n_sellers, "price": raw.price, "freight": raw.freight,
        "freight_ratio": raw.freight / (raw.price + raw.freight),
        "payment_installments": raw.payment_installments,
        "customer_state": raw.customer_state, "payment_type": raw.payment_type.fillna("missing"),
    })
    out[NUMERIC] = out[NUMERIC].astype(float)
    return out


def to_json_payload(row: pd.Series) -> dict:
    """Một đơn như service online nhận: JSON thật, timestamp là chuỗi ISO, thiếu là null."""
    d = {}
    for k, v in row.items():
        if k in TS:
            d[k] = None if pd.isna(v) else pd.Timestamp(v).isoformat()
        elif isinstance(v, (np.integer,)):
            d[k] = int(v)
        elif isinstance(v, (float, np.floating)) and np.isnan(v):
            d[k] = None
        elif v is None:
            d[k] = None
        else:
            d[k] = v.item() if hasattr(v, "item") else v
    return json.loads(json.dumps(d))


@pytest.fixture(scope="module")
def model():
    raw = make_raw(800, seed=1)
    X = reference_features(raw)
    y = (X.delay_days + np.random.default_rng(0).normal(0, 5, len(X)) > 0).astype(int)
    pre = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])
    return make_pipeline(pre, LogisticRegression(max_iter=1000)).fit(X, y)


@pytest.fixture(scope="module")
def scoring():
    return ex.module("scoring.py")


def test_make_features_hand_example(scoring):
    raw = pd.DataFrame({
        "order_id": ["a"], "order_purchase_timestamp": [pd.Timestamp("2018-01-01 10:00")],
        "order_approved_at": [pd.Timestamp("2018-01-01 12:00")],
        "order_delivered_customer_date": [pd.Timestamp("2018-01-11 10:00")],
        "order_estimated_delivery_date": [pd.Timestamp("2018-01-09 00:00")],
        "n_items": [2], "n_sellers": [1], "price": [90.0], "freight": [10.0],
        "payment_type": [None], "payment_installments": [3.0], "customer_state": ["SP"],
    })
    out = scoring.make_features(raw)
    assert list(out.columns) == ["order_id", *FEATURES]
    row = out.iloc[0]
    assert row.promised_days == pytest.approx(7 + 14 / 24)
    assert row.delivery_days == pytest.approx(10.0)
    assert row.delay_days == pytest.approx(2 + 10 / 24)
    assert row.approve_hours == pytest.approx(2.0)
    assert row.freight_ratio == pytest.approx(0.1)
    assert row.payment_type == "missing"
    assert all(out[c].dtype == np.float64 for c in NUMERIC)


def test_make_features_matches_reference_and_keeps_input(scoring):
    raw = make_raw(200, seed=2)
    before = raw.copy()
    out = scoring.make_features(raw)
    pd.testing.assert_frame_equal(raw, before)
    # kiểu chuỗi (object hay str của pandas 3) không quan trọng; cột số đã kiểm float64 ở test trên
    pd.testing.assert_frame_equal(out[FEATURES].reset_index(drop=True), reference_features(raw).reset_index(drop=True),
                                  check_dtype=False)


def test_string_timestamps_give_same_features(scoring):
    raw = make_raw(50, seed=3)
    as_text = raw.copy()
    for c in TS:
        as_text[c] = [None if pd.isna(v) else v.isoformat() for v in raw[c]]
    pd.testing.assert_frame_equal(scoring.make_features(as_text), scoring.make_features(raw))


def test_batch_writes_partition(scoring, model, tmp_path):
    raw = make_raw(120, seed=4)
    path = scoring.score_batch(model, raw, model_version="5", out_dir=tmp_path, run_date="2018-05-01")
    assert path == tmp_path / "run_date=2018-05-01" / "scores.parquet"
    out = pd.read_parquet(path)
    assert list(out.columns) == ["order_id", "score", "model_version", "run_date"]
    assert out.order_id.tolist() == raw.order_id.tolist()
    want = model.predict_proba(reference_features(raw))[:, 1]
    assert out.score.to_numpy() == pytest.approx(want, abs=1e-12)
    assert set(out.model_version) == {"5"} and set(out.run_date) == {"2018-05-01"}


def test_batch_rerun_is_idempotent(scoring, model, tmp_path):
    raw = make_raw(80, seed=5)
    for _ in range(3):
        scoring.score_batch(model, raw, model_version="5", out_dir=tmp_path, run_date="2018-05-02")
    part = tmp_path / "run_date=2018-05-02"
    assert [p.name for p in part.iterdir()] == ["scores.parquet"]
    assert len(pd.read_parquet(part / "scores.parquet")) == 80
    # chạy lại với dữ liệu ít hơn: phân vùng bị thay hẳn, không còn dòng cũ
    scoring.score_batch(model, raw.head(10), model_version="6", out_dir=tmp_path, run_date="2018-05-02")
    again = pd.read_parquet(part / "scores.parquet")
    assert len(again) == 10 and set(again.model_version) == {"6"}


def test_other_partitions_untouched(scoring, model, tmp_path):
    scoring.score_batch(model, make_raw(30, seed=6), model_version="5", out_dir=tmp_path, run_date="2018-05-03")
    scoring.score_batch(model, make_raw(40, seed=7), model_version="5", out_dir=tmp_path, run_date="2018-05-04")
    scoring.score_batch(model, make_raw(40, seed=7), model_version="5", out_dir=tmp_path, run_date="2018-05-04")
    assert len(pd.read_parquet(tmp_path / "run_date=2018-05-03" / "scores.parquet")) == 30
    assert len(pd.read_parquet(tmp_path / "run_date=2018-05-04" / "scores.parquet")) == 40


def test_online_matches_batch_for_every_order(scoring, model, tmp_path):
    raw = make_raw(150, seed=8)
    batch = pd.read_parquet(scoring.score_batch(model, raw, model_version="5", out_dir=tmp_path, run_date="2018-06-01"))
    batch = batch.set_index("order_id").score
    assert raw.order_approved_at.isna().any() and raw.payment_type.isna().any()
    for _, row in raw.iterrows():
        res = scoring.score_online(model, to_json_payload(row), model_version="5")
        assert set(res) == {"order_id", "score", "model_version"}
        assert isinstance(res["score"], float)
        assert res["score"] == pytest.approx(batch[res["order_id"]], abs=1e-12), res["order_id"]


def test_online_payload_is_not_modified(scoring, model):
    payload = to_json_payload(make_raw(1, seed=9).iloc[0])
    before = json.dumps(payload, sort_keys=True)
    scoring.score_online(model, payload, model_version="5")
    assert json.dumps(payload, sort_keys=True) == before
