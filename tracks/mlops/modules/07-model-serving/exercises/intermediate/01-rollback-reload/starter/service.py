import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
import numpy as np
from fastapi import FastAPI
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
    state = {"version": version, "model": load(model_name, version)}
    app = FastAPI()

    @app.post("/predict")
    def predict(request: PredictRequest):
        version, model = state["version"], state["model"]
        predictions = [float(value) for value in model.predict(np.array(request.rows, dtype=float))]
        return {"model_version": version, "predictions": predictions}

    return app
