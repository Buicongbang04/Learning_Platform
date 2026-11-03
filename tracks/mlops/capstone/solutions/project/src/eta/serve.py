import ipaddress
import os
import socket
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import joblib
import pandas as pd
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field

from eta.features import MAX_DISTANCE, MIN_DURATION_S, make_features
from eta.logs import get_logger, log_event

ALIAS = "champion"
TIMEZONE = "America/New_York"
logger = get_logger("eta.serve")


class TripRequest(BaseModel):
    PULocationID: int = Field(ge=1, le=265)
    DOLocationID: int = Field(ge=1, le=265)
    pickup_datetime: datetime
    trip_distance: float = Field(gt=0, le=MAX_DISTANCE)


class Prediction(BaseModel):
    eta_s: float
    model_version: str


def pin_tracking_host(uri: str) -> str:
    parts = urlsplit(uri)
    host = parts.hostname
    if not host or host == "localhost":
        return uri
    try:
        ipaddress.ip_address(host)
        return uri
    except ValueError:
        pass
    netloc = socket.gethostbyname(host) + (f":{parts.port}" if parts.port else "")
    return urlunsplit(parts._replace(netloc=netloc))


def load_model() -> tuple[object, str]:
    path = os.environ.get("ETA_MODEL_PATH")
    if path:
        return joblib.load(path), os.environ.get("ETA_MODEL_VERSION", f"file:{Path(path).name}")
    os.environ.setdefault("MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD", "false")
    import mlflow
    from mlflow import MlflowClient

    if os.environ.get("ETA_MLFLOW_PIN_IP") == "1" and os.environ.get("MLFLOW_TRACKING_URI"):
        mlflow.set_tracking_uri(pin_tracking_host(os.environ["MLFLOW_TRACKING_URI"]))
    name = os.environ.get("ETA_MODEL_NAME", "eta")
    version = MlflowClient().get_model_version_by_alias(name, ALIAS).version
    return mlflow.sklearn.load_model(f"models:/{name}/{version}"), str(version)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model, app.state.model_version = load_model()
    log_event(logger, "model_loaded", model_version=app.state.model_version)
    yield


app = FastAPI(title="ETA taxi NYC", lifespan=lifespan)


def to_local(value: datetime) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    return stamp.tz_convert(TIMEZONE).tz_localize(None) if stamp.tzinfo is not None else stamp


@app.get("/healthz")
def healthz(request: Request) -> dict:
    return {"status": "ok", "model_version": request.app.state.model_version}


@app.post("/predict", response_model=Prediction)
def predict(trip: TripRequest, request: Request, response: Response) -> Prediction:
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    frame = pd.DataFrame(
        [{"tpep_pickup_datetime": to_local(trip.pickup_datetime), "PULocationID": trip.PULocationID,
          "DOLocationID": trip.DOLocationID, "trip_distance": trip.trip_distance}]
    )
    features = make_features(frame)
    eta_s = max(float(request.app.state.model.predict(features)[0]), float(MIN_DURATION_S))
    version = request.app.state.model_version
    response.headers["x-request-id"] = request_id
    log_event(logger, "prediction", request_id=request_id, model_version=version,
              features=features.to_dict("records")[0], eta_s=round(eta_s, 1),
              latency_ms=round((time.perf_counter() - started) * 1000, 2))
    return Prediction(eta_s=eta_s, model_version=version)
