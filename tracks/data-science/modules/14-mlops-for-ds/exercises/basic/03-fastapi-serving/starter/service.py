"""API chấm điểm nguy cơ review xấu cho đơn Olist vừa giao xong."""

from __future__ import annotations

from typing import Literal

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

NUMERIC = ["promised_days", "delivery_days", "delay_days", "approve_hours", "n_items", "n_sellers",
           "price", "freight", "freight_ratio", "payment_installments"]
CATEGORICAL = ["customer_state", "payment_type"]
FEATURES = NUMERIC + CATEGORICAL


class OrderFeatures(BaseModel):
    """Feature của một đơn. TODO: thêm ràng buộc (Field(ge=...), Literal...) theo đề bài."""

    order_id: str
    promised_days: float
    delivery_days: float
    delay_days: float
    approve_hours: float | None = None
    n_items: int
    n_sellers: int
    price: float
    freight: float
    freight_ratio: float
    payment_installments: float | None = None
    customer_state: str
    payment_type: str


class PredictRequest(BaseModel):
    # TODO: từ 1 tới 1000 đơn mỗi request
    orders: list[OrderFeatures]


def create_app(model, model_version: str, threshold: float = 0.5) -> FastAPI:
    """App FastAPI phục vụ `model` (có predict_proba nhận DataFrame).

    GET  /health  -> {"status": "ok", "model_version": ...}
    POST /predict -> {"model_version": ..., "predictions": [{"order_id", "score", "high_risk"}, ...]}
    """
    # TODO: app = FastAPI(...); khai báo hai route; gọi model một lần cho cả batch
    raise NotImplementedError
