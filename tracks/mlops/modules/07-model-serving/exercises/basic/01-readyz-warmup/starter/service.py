from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

WARMUP_ROWS = [[5.0, 8, 1], [12.0, 17, 2], [2.0, 23, 1]]
MAX_ROWS = 100


class PredictRequest(BaseModel):
    rows: list[list[float]]


def create_app(load_model, warmup_rows=WARMUP_ROWS, predict_timeout: float = 1.0) -> FastAPI:
    app = FastAPI()
    state = {"model": load_model()}

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        return {"ready": True, "model_version": state["model"].version}

    @app.post("/predict")
    def predict(request: PredictRequest):
        model = state["model"]
        return {"model_version": model.version, "predictions": model.predict(request.rows)}

    return app
