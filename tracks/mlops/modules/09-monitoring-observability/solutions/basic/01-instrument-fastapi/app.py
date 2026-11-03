import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, Info, generate_latest
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
    requests_total = Counter("http_requests", "Số yêu cầu HTTP", ["method", "route", "status"], registry=registry)
    latency = Histogram("http_request_duration_seconds", "Độ trễ yêu cầu", ["method", "route"],
                        buckets=LATENCY_BUCKETS, registry=registry)
    prediction = Histogram("eta_prediction_seconds", "Phân phối ETA trả về", buckets=PREDICTION_BUCKETS, registry=registry)
    fallback = Counter("eta_fallback", "Số lần dùng heuristic thay model", registry=registry)
    info = Info("eta_model", "Model đang chạy", registry=registry)
    info.info({"version": str(model.version)})

    app = FastAPI()

    @app.middleware("http")
    async def observe(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse({"detail": "internal error"}, status_code=500)
        route = request.scope.get("route")
        path = getattr(route, "path", None)
        label = path if path in KNOWN_ROUTES else "unmatched"
        requests_total.labels(request.method, label, str(response.status_code)).inc()
        latency.labels(request.method, label).observe(time.perf_counter() - started)
        return response

    @app.post("/predict")
    def predict(body: PredictIn) -> dict:
        used_fallback = False
        try:
            eta = float(model.predict(body.trip_distance_km))
        except ModelError:
            eta = fallback_eta(body.trip_distance_km)
            used_fallback = True
            fallback.inc()
        prediction.observe(eta)
        return {"eta_seconds": eta, "model_version": str(model.version), "fallback": used_fallback}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    return app
