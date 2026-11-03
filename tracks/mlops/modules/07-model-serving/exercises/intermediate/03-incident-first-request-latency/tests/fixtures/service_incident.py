import threading
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

_ZONES: dict[int, float] | None = None
_LOCK = threading.Lock()


class PredictRequest(BaseModel):
    rows: list[list[float]]


def build_zone_table() -> dict[int, float]:
    time.sleep(0.5)
    return {zone: round((zone % 7) * 0.35, 2) for zone in range(1, 266)}


def zone_table() -> dict[int, float]:
    global _ZONES
    if _ZONES is None:
        with _LOCK:
            if _ZONES is None:
                _ZONES = build_zone_table()
    return _ZONES


def eta_minutes(distance_km: float, hour: float, zone: float) -> float:
    rush = 3.0 if 7 <= hour <= 9 or 16 <= hour <= 19 else 0.0
    return round(4 + 2.6 * distance_km + rush + zone_table().get(int(zone), 0.0), 3)


def create_app() -> FastAPI:
    app = FastAPI()
    state = {"ready": False}

    @app.on_event("startup")
    def startup() -> None:
        state["ready"] = True

    @app.get("/readyz")
    def readyz():
        if not state["ready"]:
            raise HTTPException(503, "chưa sẵn sàng")
        return {"ready": True}

    @app.post("/predict")
    def predict(request: PredictRequest):
        return {"model_version": 3, "predictions": [eta_minutes(*row) for row in request.rows]}

    return app
