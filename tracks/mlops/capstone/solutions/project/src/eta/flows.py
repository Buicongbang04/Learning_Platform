import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from prefect import flow, task
from prefect.cache_policies import NONE

from eta.clock import add_months, months_between
from eta.config import Config, load_config
from eta.labels import labels_for, month_trips
from eta.logs import PREDICTION_LOG_COLUMNS, get_logger, log_event

ALIAS = "champion"
CODE_FILES = ("data.py", "features.py", "train.py", "labels.py", "zone_features.py", "registry.py", "flows.py")
logger = get_logger("eta.flows")


def code_version() -> str:
    digest = hashlib.sha256()
    for name in CODE_FILES:
        digest.update(name.encode())
        digest.update((Path(__file__).parent / name).read_bytes())
    return digest.hexdigest()[:16]


def _speed_table(config: Config) -> pd.DataFrame | None:
    from eta.zone_features import read_speed_table

    return read_speed_table(config.speed_table) if config.speed_table else None


def _config(config_path: str, months: list[str] | None = None) -> Config:
    config = load_config(Path(config_path))
    if months is not None:
        config.months = list(months)
    return config


def _train_key(context, parameters: dict) -> str:
    config: Config = parameters["config"]
    payload = {
        "data_version": parameters["data_version"],
        "months": config.months,
        "sample_rows": config.sample_rows,
        "seed": config.seed,
        "model_params": config.model_params,
        "mlflow_uri": config.mlflow_uri,
        "model_name": config.model_name,
        "speed_table": str(config.speed_table) if config.speed_table else None,
        "code_version": code_version(),
    }
    return "eta-train-" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:32]


@task(retries=2, retry_delay_seconds=1, cache_policy=NONE)
def fingerprint(config: Config) -> str:
    from eta.data import month_path
    from eta.lineage import data_version

    paths = [month_path(config.data_dir, m) for m in config.months]
    return data_version(paths + ([config.speed_table] if config.speed_table else []))


@task(cache_key_fn=_train_key, persist_result=True)
def train_and_register(config: Config, data_version: str) -> str:
    from eta.features import build_features
    from eta.registry import log_and_register
    from eta.train import evaluate, time_split, train
    from eta.zone_features import attach_speed

    frame = pd.concat([month_trips(m, config) for m in config.months], ignore_index=True)
    table = _speed_table(config)
    if table is not None:
        frame = attach_speed(frame, table)
    train_df, test_df = time_split(frame)
    model = train(*build_features(train_df), {"random_state": config.seed, **config.model_params})
    metrics = evaluate(model, *build_features(test_df))
    version = log_and_register(model, metrics, config, data_version)
    log_event(logger, "trained", months=config.months, data_version=data_version, model_version=version, **metrics)
    return version


def _registered(config: Config, version: str, data_version: str) -> bool:
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    try:
        found = MlflowClient(tracking_uri=config.mlflow_uri).get_model_version(config.model_name, version)
    except MlflowException:
        return False
    return found.tags.get("data_version") == data_version


@flow(name="eta-train")
def train_flow(config_path: str, months: list[str]) -> str:
    config = _config(config_path, months)
    data_version = fingerprint(config)
    version = train_and_register(config, data_version)
    if _registered(config, version, data_version):
        return version
    log_event(logger, "stale_cache", model_name=config.model_name, model_version=version, data_version=data_version)
    return train_and_register.with_options(refresh_cache=True)(config, data_version)


def _champion(config: Config) -> tuple[object, str] | None:
    import mlflow
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    client = MlflowClient(tracking_uri=config.mlflow_uri)
    try:
        version = client.get_model_version_by_alias(config.model_name, ALIAS).version
    except MlflowException:
        return None
    mlflow.set_tracking_uri(config.mlflow_uri)
    return mlflow.sklearn.load_model(f"models:/{config.model_name}/{version}"), str(version)


@task(retries=2, retry_delay_seconds=1, cache_policy=NONE)
def score_month(month: str, config: Config, out_dir: str) -> str:
    from eta.features import MIN_DURATION_S, make_features
    from eta.zone_features import prepare

    champion = _champion(config)
    if champion is None:
        raise RuntimeError(f"{config.model_name} chưa có alias {ALIAS}: chạy train_flow và promote trước khi chấm")
    model, version = champion
    trips = month_trips(month, config)
    eta = np.maximum(model.predict(make_features(prepare(trips, model, _speed_table(config)))), float(MIN_DURATION_S))
    frame = pd.DataFrame({
        "request_id": trips["request_id"],
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version": version,
        "variant": "batch",
        "PULocationID": trips["PULocationID"].astype("int64"),
        "DOLocationID": trips["DOLocationID"].astype("int64"),
        "pickup_datetime": trips["tpep_pickup_datetime"].dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "trip_distance": trips["trip_distance"].astype("float64"),
        "eta_s": eta.astype("float64"),
    })[PREDICTION_LOG_COLUMNS]
    path = Path(out_dir) / f"predictions_{month}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    frame.to_parquet(tmp, index=False)
    tmp.replace(path)
    log_event(logger, "scored", month=month, model_version=version, rows=len(frame), path=str(path))
    return str(path)


@flow(name="eta-batch-score")
def batch_score_flow(month: str, config_path: str, out_dir: str) -> str:
    return score_month(month, _config(config_path), out_dir)


def realized_mae(month: str, as_of: str, config: Config, out_dir: str) -> float | None:
    truth = labels_for(month, as_of, config)
    if truth is None:
        return None
    scored = pd.read_parquet(Path(out_dir) / f"predictions_{month}.parquet", columns=["request_id", "eta_s"])
    joined = scored.merge(truth, on="request_id", how="inner", validate="one_to_one")
    if joined.empty:
        return None
    value = float(np.abs(joined["duration_s"] - joined["eta_s"]).mean())
    return None if math.isnan(value) else value


@flow(name="eta-replay")
def replay_flow(start: str, end: str, config_path: str, out_dir: str) -> list[dict]:
    from mlflow import MlflowClient

    config = _config(config_path)
    if _champion(config) is None:
        version = train_flow(config_path, [add_months(start, -1)])
        MlflowClient(tracking_uri=config.mlflow_uri).set_registered_model_alias(config.model_name, ALIAS, version)
    rows = []
    for now in months_between(start, end):
        path = score_month(now, config, out_dir)
        scored = pd.read_parquet(path, columns=["model_version"])
        rows.append({"month": now, "model_version": str(scored["model_version"].iloc[0]), "n_scored": len(scored)})
        log_event(logger, "clock_tick", now=now, scored=len(scored))
    for row in rows:
        row["mae"] = realized_mae(row["month"], end, config, out_dir)
        row["as_of"] = end
    Path(out_dir, "replay.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows
