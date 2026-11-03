from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest


def create_app() -> FastAPI:
    registry = CollectorRegistry()
    requests_total = Counter("http_requests", "Số yêu cầu HTTP", ["method", "route", "code"], registry=registry)
    latency = Histogram("http_request_duration_seconds", "Độ trễ", ["method", "route"], registry=registry)
    app = FastAPI()

    @app.middleware("http")
    async def observe(request: Request, call_next):
        response = await call_next(request)
        if request.url.path != "/metrics":
            route = getattr(request.scope.get("route"), "path", "unmatched")
            requests_total.labels(request.method, route, str(response.status_code)).inc()
            latency.labels(request.method, route).observe(0.01)
        return response

    @app.post("/predict")
    def predict(body: dict) -> JSONResponse:
        mode = body.get("mode", "ok")
        if mode == "error":
            return JSONResponse({"detail": "model crashed"}, status_code=500)
        if mode == "unavailable":
            return JSONResponse({"detail": "model not loaded"}, status_code=503)
        return JSONResponse({"eta_seconds": 620.0})

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    return app
