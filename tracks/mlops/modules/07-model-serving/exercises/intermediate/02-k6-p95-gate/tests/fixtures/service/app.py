import asyncio
import os

import joblib
from fastapi import FastAPI
from pydantic import BaseModel

BUNDLE = joblib.load("model.joblib")
MODEL = BUNDLE["model"]
SLOW_MS = float(os.environ.get("SLOW_MS", "0"))
app = FastAPI()


class PredictRequest(BaseModel):
    rows: list[list[float]]


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/predict")
async def predict(request: PredictRequest):
    if SLOW_MS:
        await asyncio.sleep(SLOW_MS / 1000)
    return {"model_version": 1, "predictions": [float(v) for v in MODEL.predict(request.rows)]}
