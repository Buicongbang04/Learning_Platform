import asyncio
import math
import threading

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

WARMUP_ROWS = [[5.0, 8, 1], [12.0, 17, 2], [2.0, 23, 1]]
MAX_ROWS = 100


class PredictRequest(BaseModel):
    rows: list[list[float]]


def validate(rows: list[list[float]]) -> None:
    if not 1 <= len(rows) <= MAX_ROWS:
        raise HTTPException(422, f"cần 1..{MAX_ROWS} dòng")
    for row in rows:
        if len(row) != 3 or not all(math.isfinite(value) for value in row):
            raise HTTPException(422, "mỗi dòng cần đúng 3 số hữu hạn")
        if not 0 <= row[1] <= 23:
            raise HTTPException(422, "hour phải trong 0..23")


def create_app(load_model, warmup_rows=WARMUP_ROWS, predict_timeout: float = 1.0) -> FastAPI:
    state = {"model": None, "ready": False, "error": None}

    def boot() -> None:
        try:
            model = load_model()
            for _ in range(3):
                model.predict(warmup_rows)
            state["model"] = model
            state["ready"] = True
        except Exception as error:
            state["error"] = f"{type(error).__name__}: {error}"

    async def lifespan(app):
        threading.Thread(target=boot, daemon=True).start()
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        if not state["ready"]:
            raise HTTPException(503, {"ready": False, "error": state["error"]})
        return {"ready": True, "model_version": state["model"].version}

    @app.post("/predict")
    async def predict(request: PredictRequest):
        if not state["ready"]:
            raise HTTPException(503, "model chưa sẵn sàng")
        validate(request.rows)
        model = state["model"]
        try:
            predictions = await asyncio.wait_for(run_in_threadpool(model.predict, request.rows), predict_timeout)
        except asyncio.TimeoutError:
            raise HTTPException(504, "predict quá thời hạn")
        return {"model_version": model.version, "predictions": predictions}

    return app
