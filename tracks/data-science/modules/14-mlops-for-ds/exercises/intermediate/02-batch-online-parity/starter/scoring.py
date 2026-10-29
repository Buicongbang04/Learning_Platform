"""Chấm điểm review xấu theo hai đường: batch (hằng ngày) và online (từng đơn), cùng một logic feature."""

from __future__ import annotations

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
    # TODO
    raise NotImplementedError


def score_batch(model, orders: pd.DataFrame, model_version: str, out_dir, run_date: str) -> Path:
    """Chấm mọi đơn, ghi out_dir/run_date=<run_date>/scores.parquet và trả đường dẫn đó.

    Cột: order_id, score (xác suất review xấu), model_version, run_date (chuỗi).
    Chạy lại cùng run_date thì thay toàn bộ phân vùng đó (idempotent); phân vùng khác giữ nguyên.
    """
    # TODO: make_features -> model.predict_proba -> ghi parquet; xoá phân vùng cũ trước khi ghi
    raise NotImplementedError


def score_online(model, payload: dict, model_version: str) -> dict:
    """Chấm một đơn nhận qua JSON (timestamp là chuỗi ISO, thiếu là None).

    Trả {"order_id": str, "score": float, "model_version": str}. Score phải khớp đường batch.
    """
    # TODO: dùng lại make_features, không viết logic feature thứ hai
    raise NotImplementedError
