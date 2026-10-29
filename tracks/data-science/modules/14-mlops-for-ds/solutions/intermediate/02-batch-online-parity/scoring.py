"""Chấm điểm review xấu theo hai đường: batch (hằng ngày) và online (từng đơn), cùng một logic feature."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd

NUMERIC = ["promised_days", "delivery_days", "delay_days", "approve_hours", "n_items", "n_sellers",
           "price", "freight", "freight_ratio", "payment_installments"]
CATEGORICAL = ["customer_state", "payment_type"]
FEATURES = NUMERIC + CATEGORICAL
TIMESTAMPS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_customer_date",
              "order_estimated_delivery_date"]


def make_features(orders: pd.DataFrame) -> pd.DataFrame:
    """Từ đơn thô (mỗi đơn một dòng) ra bảng cột order_id + FEATURES, đúng thứ tự đó.

    - Cột thời gian có thể là datetime hoặc chuỗi ISO; thiếu (None/NaT) thì feature tương ứng là NaN.
    - promised_days = (estimated - purchase) theo ngày; delivery_days = (delivered - purchase);
      delay_days = (delivered - estimated); approve_hours = (approved - purchase) theo giờ.
    - freight_ratio = freight / (price + freight).
    - Mọi cột NUMERIC là float64; payment_type thiếu thành "missing".
    - Không sửa DataFrame đầu vào; giữ thứ tự dòng.
    """
    ts = {c: pd.to_datetime(orders[c]) for c in TIMESTAMPS}
    day, hour = pd.Timedelta(days=1), pd.Timedelta(hours=1)
    price = orders["price"].astype(float)
    freight = orders["freight"].astype(float)
    out = pd.DataFrame({
        "order_id": orders["order_id"].astype(str),
        "promised_days": (ts["order_estimated_delivery_date"] - ts["order_purchase_timestamp"]) / day,
        "delivery_days": (ts["order_delivered_customer_date"] - ts["order_purchase_timestamp"]) / day,
        "delay_days": (ts["order_delivered_customer_date"] - ts["order_estimated_delivery_date"]) / day,
        "approve_hours": (ts["order_approved_at"] - ts["order_purchase_timestamp"]) / hour,
        "n_items": orders["n_items"], "n_sellers": orders["n_sellers"],
        "price": price, "freight": freight, "freight_ratio": freight / (price + freight),
        "payment_installments": orders["payment_installments"],
        "customer_state": orders["customer_state"],
        "payment_type": orders["payment_type"].astype(object).where(orders["payment_type"].notna(), "missing"),
    }, index=orders.index)
    out[NUMERIC] = out[NUMERIC].astype("float64")
    return out


def _score(model, features: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(features[FEATURES])[:, 1]


def score_batch(model, orders: pd.DataFrame, model_version: str, out_dir, run_date: str) -> Path:
    """Chấm mọi đơn, ghi out_dir/run_date=<run_date>/scores.parquet và trả đường dẫn đó.

    Cột: order_id, score (xác suất review xấu), model_version, run_date (chuỗi).
    Chạy lại cùng run_date thì thay toàn bộ phân vùng đó (idempotent); phân vùng khác giữ nguyên.
    """
    features = make_features(orders)
    result = pd.DataFrame({
        "order_id": features["order_id"].to_numpy(),
        "score": _score(model, features),
        "model_version": str(model_version),
        "run_date": str(run_date),
    })
    partition = Path(out_dir) / f"run_date={run_date}"
    staging = Path(out_dir) / f".run_date={run_date}.tmp"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    result.to_parquet(staging / "scores.parquet", index=False)
    # Ghi xong ở thư mục tạm rồi mới thay phân vùng: job chết giữa chừng không để lại phân vùng dở
    shutil.rmtree(partition, ignore_errors=True)
    staging.rename(partition)
    return partition / "scores.parquet"


def score_online(model, payload: dict, model_version: str) -> dict:
    """Chấm một đơn nhận qua JSON (timestamp là chuỗi ISO, thiếu là None).

    Trả {"order_id": str, "score": float, "model_version": str}. Score phải khớp đường batch.
    """
    features = make_features(pd.DataFrame([payload]))
    return {"order_id": str(features["order_id"].iloc[0]),
            "score": float(_score(model, features)[0]),
            "model_version": str(model_version)}
