import hashlib
import json
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from eta.features import MAX_DISTANCE, MIN_DURATION_S, make_features
from eta.logs import PREDICTION_LOG_COLUMNS, get_logger, log_event
from eta.zone_features import MissingSpeedTable, needs_speed, prepare, read_speed_table

ALIAS = "champion"
CHALLENGER_ALIAS = "challenger"
TIMEZONE = "America/New_York"
WARMUP_TRIP = {"PULocationID": 161, "DOLocationID": 236, "pickup_datetime": datetime(2019, 1, 15, 8, 30), "trip_distance": 2.4}
logger = get_logger("eta.serve")

FALLBACKS = Counter("eta_fallback", "Request canary lỗi, đã trả kết quả của champion")
SHADOW_ERRORS = Counter("eta_shadow_errors", "Lỗi khi chạy model shadow (không ảnh hưởng response)")


class TripRequest(BaseModel):
    PULocationID: int = Field(ge=1, le=265)
    DOLocationID: int = Field(ge=1, le=265)
    pickup_datetime: datetime
    trip_distance: float = Field(gt=0, le=MAX_DISTANCE)


class Prediction(BaseModel):
    eta_s: float
    model_version: str
    variant: str


@dataclass(frozen=True)
class Loaded:
    model: object
    version: str


@dataclass(frozen=True)
class Models:
    champion: Loaded
    challenger: Loaded | None
    speed: pd.DataFrame | None = None


def route(request_id: str, weight: float) -> str:
    if weight <= 0:
        return "champion"
    bucket = int.from_bytes(hashlib.sha256(request_id.encode("utf-8")).digest()[:8], "big") / 2**64
    return "canary" if bucket < weight else "champion"


def _from_file(path: str, version_env: str) -> Loaded:
    return Loaded(joblib.load(path), os.environ.get(version_env) or f"file:{Path(path).name}")


def _from_registry(name: str, alias: str, required: bool) -> Loaded | None:
    import mlflow
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    try:
        version = str(MlflowClient().get_model_version_by_alias(name, alias).version)
    except MlflowException:
        if required:
            raise
        return None
    return Loaded(mlflow.sklearn.load_model(f"models:/{name}/{version}"), version)


def load_models() -> Models:
    path = os.environ.get("ETA_MODEL_PATH")
    if path:
        challenger = os.environ.get("ETA_CHALLENGER_PATH")
        return Models(_from_file(path, "ETA_MODEL_VERSION"),
                      _from_file(challenger, "ETA_CHALLENGER_VERSION") if challenger else None)
    os.environ.setdefault("MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD", "false")
    name = os.environ.get("ETA_MODEL_NAME", "eta")
    return Models(_from_registry(name, ALIAS, True), _from_registry(name, CHALLENGER_ALIAS, False))


def canary_weight() -> float:
    weight = float(os.environ.get("ETA_CANARY_WEIGHT") or 0)
    if not 0 <= weight <= 1:
        raise ValueError(f"ETA_CANARY_WEIGHT phải trong [0, 1], nhận {weight}")
    return weight


def load_speed_table() -> pd.DataFrame | None:
    path = os.environ.get("ETA_SPEED_TABLE")
    return read_speed_table(path) if path else None


def check_speed(models: Models, speed: pd.DataFrame | None) -> None:
    for role, loaded in (("champion", models.champion), ("challenger", models.challenger)):
        if loaded is not None and needs_speed(loaded.model) and speed is None:
            raise MissingSpeedTable(f"{role} {loaded.version} cần avg_speed_mph nhưng chưa đặt ETA_SPEED_TABLE")


def to_local(value: datetime) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    return stamp.tz_convert(TIMEZONE).tz_localize(None) if stamp.tzinfo is not None else stamp


def trip_frame(trip: dict) -> pd.DataFrame:
    return pd.DataFrame([{"tpep_pickup_datetime": to_local(trip["pickup_datetime"]), "PULocationID": trip["PULocationID"],
                          "DOLocationID": trip["DOLocationID"], "trip_distance": trip["trip_distance"]}])


def predict_one(loaded: Loaded, frame: pd.DataFrame, speed: pd.DataFrame | None) -> float:
    features = make_features(prepare(frame, loaded.model, speed))
    return max(float(loaded.model.predict(features)[0]), float(MIN_DURATION_S))


def warmup(models: Models, speed: pd.DataFrame | None) -> float:
    started = time.perf_counter()
    frame = trip_frame(WARMUP_TRIP)
    predict_one(models.champion, frame, speed)
    if models.challenger is not None:
        try:
            predict_one(models.challenger, frame, speed)
        except Exception as err:
            log_event(logger, "challenger_warmup_failed", model_version=models.challenger.version, error=repr(err))
    return round((time.perf_counter() - started) * 1000, 2)


class PredictionLog:
    def __init__(self, path: str | None):
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, request_id: str, version: str, variant: str, trip: dict, frame: pd.DataFrame, eta_s: float) -> None:
        row = {
            "request_id": request_id,
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "model_version": version,
            "variant": variant,
            "PULocationID": int(trip["PULocationID"]),
            "DOLocationID": int(trip["DOLocationID"]),
            "pickup_datetime": frame["tpep_pickup_datetime"].iloc[0].isoformat(),
            "trip_distance": float(trip["trip_distance"]),
            "eta_s": round(eta_s, 3),
        }
        log_event(logger, "prediction", **row)
        if self.path is None:
            return
        line = json.dumps({key: row[key] for key in PREDICTION_LOG_COLUMNS}, ensure_ascii=False)
        with self.lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = app.state
    state.ready = False
    state.models = None
    state.not_ready = "đang nạp"
    state.canary_weight = canary_weight()
    state.shadow = os.environ.get("ETA_SHADOW", "0") == "1"
    state.log = PredictionLog(os.environ.get("ETA_PREDICTION_LOG"))
    state.reload_lock = threading.Lock()
    try:
        install(state)
    except MissingSpeedTable as err:
        state.not_ready = str(err)
        log_event(logger, "not_ready", reason=state.not_ready)
    yield
    state.ready = False
    state.models = None
    state.not_ready = "đang tắt"
    log_event(logger, "shutdown")


def install(state) -> dict:
    speed = load_speed_table()
    models = replace(load_models(), speed=speed)
    check_speed(models, speed)
    warm_ms = warmup(models, speed)
    state.models, state.ready, state.not_ready = models, True, None
    info = {"champion": models.champion.version, "challenger": models.challenger.version if models.challenger else None}
    log_event(logger, "ready", **info, canary_weight=state.canary_weight, shadow=state.shadow, warmup_ms=warm_ms)
    return info


app = FastAPI(title="ETA taxi NYC", lifespan=lifespan)


def current(request: Request) -> Models | None:
    if not getattr(request.app.state, "ready", False):
        return None
    return getattr(request.app.state, "models", None)


@app.get("/healthz")
def healthz(request: Request) -> dict:
    models = current(request)
    return {"status": "ok", "model_version": models.champion.version if models else None}


@app.get("/readyz")
def readyz(request: Request):
    models = current(request)
    if models is None:
        reason = getattr(request.app.state, "not_ready", None) or "chưa khởi động"
        return JSONResponse({"status": "not_ready", "reason": reason}, status_code=503)
    state = request.app.state
    return {"status": "ready", "model_version": models.champion.version,
            "challenger": models.challenger.version if models.challenger else None,
            "canary_weight": state.canary_weight, "shadow": state.shadow}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def run_shadow(state, models: Models, request_id: str, trip: dict, frame: pd.DataFrame) -> None:
    challenger = models.challenger
    try:
        eta_s = predict_one(challenger, frame, models.speed)
    except Exception as err:
        SHADOW_ERRORS.inc()
        log_event(logger, "shadow_failed", request_id=request_id, model_version=challenger.version, error=repr(err))
        return
    state.log.write(request_id, challenger.version, "shadow", trip, frame, eta_s)


@app.post("/predict", response_model=Prediction)
def predict(trip: TripRequest, request: Request, response: Response, background: BackgroundTasks) -> Prediction:
    models = current(request)
    if models is None:
        raise HTTPException(status_code=503, detail="model chưa sẵn sàng")
    state = request.app.state
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    response.headers["x-request-id"] = request_id
    payload = trip.model_dump()
    frame = trip_frame(payload)
    variant = route(request_id, state.canary_weight) if models.challenger is not None else "champion"
    served = models.champion
    if variant == "canary":
        try:
            eta_s = predict_one(models.challenger, frame, models.speed)
            served = models.challenger
        except Exception as err:
            FALLBACKS.inc()
            log_event(logger, "canary_fallback", request_id=request_id, model_version=models.challenger.version, error=repr(err))
            variant = "champion"
    if variant == "champion":
        eta_s = predict_one(models.champion, frame, models.speed)
    state.log.write(request_id, served.version, variant, payload, frame, eta_s)
    if state.shadow and models.challenger is not None and variant == "champion":
        background.add_task(run_shadow, state, models, request_id, payload, frame)
    return Prediction(eta_s=eta_s, model_version=served.version, variant=variant)


@app.post("/admin/reload")
def reload(request: Request) -> dict:
    token = os.environ.get("ETA_ADMIN_TOKEN")
    if token and request.headers.get("x-admin-token") != token:
        raise HTTPException(status_code=403, detail="sai X-Admin-Token")
    state = request.app.state
    if not hasattr(state, "reload_lock"):
        raise HTTPException(status_code=503, detail="app chưa khởi động")
    with state.reload_lock:
        previous = state.models
        try:
            info = install(state)
        except Exception as err:
            log_event(logger, "reload_failed", error=repr(err), kept=previous.champion.version if previous else None)
            raise HTTPException(status_code=500, detail=f"nạp lại thất bại, giữ bộ model cũ: {err!r}") from err
    log_event(logger, "reloaded", previous=previous.champion.version if previous else None, **info)
    return info
