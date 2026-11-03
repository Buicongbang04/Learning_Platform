from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CollectorRegistry
from pydantic import BaseModel, Field

LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
PREDICTION_BUCKETS = (60, 120, 300, 600, 900, 1200, 1800, 3600)
KNOWN_ROUTES = {"/predict", "/health"}


class ModelError(Exception):
    pass


class DefaultModel:
    version = "3"

    def predict(self, km: float) -> float:
        return 300.0 + 110.0 * km


class PredictIn(BaseModel):
    trip_distance_km: float = Field(ge=0, le=500)


def fallback_eta(km: float) -> float:
    return 240.0 + 150.0 * km


def create_app(model=None) -> FastAPI:
    model = model or DefaultModel()
    registry = CollectorRegistry()
    # TODO: khai báo các metric (counter, histogram, info) trên `registry` này

    app = FastAPI()

    # TODO: middleware "http" đo mọi yêu cầu trừ /metrics

    @app.post("/predict")
    def predict(body: PredictIn) -> dict:
        used_fallback = False
        try:
            eta = float(model.predict(body.trip_distance_km))
        except ModelError:
            eta = fallback_eta(body.trip_distance_km)
            used_fallback = True
        return {"eta_seconds": eta, "model_version": str(model.version), "fallback": used_fallback}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response("TODO", status_code=501, media_type="text/plain")

    return app
