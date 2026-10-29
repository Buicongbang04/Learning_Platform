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

PaymentType = Literal["credit_card", "boleto", "voucher", "debit_card", "not_defined", "missing"]


class OrderFeatures(BaseModel):
    """Feature của một đơn, kèm ràng buộc miền giá trị."""

    order_id: str
    promised_days: float = Field(ge=0)
    delivery_days: float = Field(ge=0)
    delay_days: float                         # âm là giao sớm, dương là giao trễ
    approve_hours: float | None = Field(default=None, ge=0)
    n_items: int = Field(ge=1)
    n_sellers: int = Field(ge=1)
    price: float = Field(ge=0)
    freight: float = Field(ge=0)
    freight_ratio: float = Field(ge=0, le=1)
    payment_installments: float | None = Field(default=None, ge=0)
    customer_state: str = Field(min_length=2, max_length=2)
    payment_type: PaymentType


class PredictRequest(BaseModel):
    orders: list[OrderFeatures] = Field(min_length=1, max_length=1000)


class Prediction(BaseModel):
    order_id: str
    score: float
    high_risk: bool


class PredictResponse(BaseModel):
    model_version: str
    predictions: list[Prediction]


def create_app(model, model_version: str, threshold: float = 0.5) -> FastAPI:
    """App FastAPI phục vụ `model` (có predict_proba nhận DataFrame).

    GET  /health  -> {"status": "ok", "model_version": ...}
    POST /predict -> {"model_version": ..., "predictions": [{"order_id", "score", "high_risk"}, ...]}
    """
    app = FastAPI(title="olist-bad-review", version=model_version)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "model_version": model_version}

    @app.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        rows = [order.model_dump() for order in request.orders]
        # None -> NaN để imputer trong pipeline xử lý; cột đúng thứ tự lúc train
        X = pd.DataFrame(rows, columns=["order_id", *FEATURES])
        X[NUMERIC] = X[NUMERIC].astype(float)
        scores = model.predict_proba(X[FEATURES])[:, 1]
        return PredictResponse(
            model_version=model_version,
            predictions=[Prediction(order_id=o, score=float(s), high_risk=bool(s >= threshold))
                         for o, s in zip(X["order_id"], scores)],
        )

    return app
