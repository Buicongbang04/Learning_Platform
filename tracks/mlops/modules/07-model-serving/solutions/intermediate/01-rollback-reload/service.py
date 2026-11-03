import os
import threading

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
import numpy as np
from fastapi import FastAPI, Header, HTTPException
from mlflow import MlflowClient
from pydantic import BaseModel


class PredictRequest(BaseModel):
    rows: list[list[float]]


def resolve(client: MlflowClient, model_name: str, alias: str) -> int:
    try:
        return int(client.get_model_version_by_alias(model_name, alias).version)
    except Exception as error:
        raise LookupError(f"{model_name}@{alias} không tồn tại") from error


def load(model_name: str, version: int):
    return mlflow.pyfunc.load_model(f"models:/{model_name}/{version}")


def create_app(tracking_uri: str, model_name: str, admin_token: str, alias: str = "champion") -> FastAPI:
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri)
    version = resolve(client, model_name, alias)
    state = {"current": (version, load(model_name, version))}
    reload_lock = threading.Lock()
    app = FastAPI()

    @app.post("/predict")
    def predict(request: PredictRequest):
        version, model = state["current"]
        predictions = [float(value) for value in model.predict(np.array(request.rows, dtype=float))]
        return {"model_version": version, "predictions": predictions}

    @app.post("/admin/reload")
    def reload(x_admin_token: str | None = Header(default=None)):
        if x_admin_token != admin_token:
            raise HTTPException(401, "thiếu hoặc sai X-Admin-Token")
        with reload_lock:
            previous = state["current"][0]
            try:
                target = resolve(client, model_name, alias)
                if target == previous:
                    return {"changed": False, "previous_version": previous, "model_version": previous}
                model = load(model_name, target)
            except Exception as error:
                raise HTTPException(409, f"reload thất bại, giữ version {previous}: {error}")
            state["current"] = (target, model)
        return {"changed": True, "previous_version": previous, "model_version": target}

    return app
