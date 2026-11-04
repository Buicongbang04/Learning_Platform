"""Retrain ETA bằng Ray Tune: nhiều trial song song trên nhiều worker, mỗi trial checkpoint định kỳ và chịu worker bị kill.

GBDT dựng cây tuần tự, cây sau học phần dư của cây trước: không chia "mỗi worker một phần cây" được. Data-parallel GBDT
(LightGBM/XGBoost distributed) chia **dữ liệu** và allreduce histogram mỗi cây, chỉ đáng khi dữ liệu không vừa một máy;
mẫu ETA vài trăm nghìn dòng vừa RAM một worker. Song song có ích ở đây là **giữa các cấu hình**: mỗi trial một worker,
cùng dữ liệu (qua object store), cùng số cây. Mỗi trial train tiếp từ checkpoint (`warm_start`) sau mỗi `every` cây.
"""

import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from eta.config import Config
from eta.features import build_features, feature_columns
from eta.train import build_pipeline, evaluate

SPACE = {"learning_rate": [0.05, 0.1], "max_leaf_nodes": [31, 63]}
METRIC = "mae"
MODEL_FILE = "model.joblib"


@dataclass
class Retrained:
    model: object
    metrics: dict
    params: dict
    trials: int


def _trial(config: dict, train: pd.DataFrame, valid: pd.DataFrame, rounds: int, every: int) -> None:
    from ray import tune

    X, y = build_features(train)
    X_valid, y_valid = build_features(valid)
    X = X[feature_columns(X)]
    checkpoint = tune.get_checkpoint()
    if checkpoint is not None:
        with checkpoint.as_directory() as folder:
            model = joblib.load(Path(folder) / MODEL_FILE)
        trees = model[-1].n_iter_
    else:
        model = build_pipeline({**config, "max_iter": 1, "early_stopping": False, "warm_start": True, "random_state": 0})
        trees = 0
    while trees < rounds:
        model.set_params(model__max_iter=min(trees + every, rounds))
        model.fit(X, y)
        trees = model[-1].n_iter_
        metrics = evaluate(model, X_valid, y_valid)
        with tempfile.TemporaryDirectory() as folder:
            joblib.dump(model, Path(folder) / MODEL_FILE)
            tune.report({**metrics, "trees": trees}, checkpoint=tune.Checkpoint.from_directory(folder))


def retrain(train: pd.DataFrame, valid: pd.DataFrame, storage_path: str, *, name: str = "eta-retrain",
            workers: int = 2, rounds: int = 200, every: int = 20, max_failures: int = 2) -> Retrained:
    from ray import tune

    if workers < 1 or every < 1 or rounds < every or max_failures < 1:
        raise ValueError("cần workers >= 1, 1 <= every <= rounds, max_failures >= 1")
    trainable = tune.with_resources(
        tune.with_parameters(_trial, train=train, valid=valid, rounds=rounds, every=every), {"cpu": 1})
    tuner = tune.Tuner(
        trainable,
        param_space={key: tune.grid_search(values) for key, values in SPACE.items()},
        tune_config=tune.TuneConfig(metric=METRIC, mode="min", max_concurrent_trials=workers),
        run_config=tune.RunConfig(
            name=name, storage_path=storage_path, verbose=0,
            failure_config=tune.FailureConfig(max_failures=max_failures),
            checkpoint_config=tune.CheckpointConfig(num_to_keep=2),
        ),
    )
    grid = tuner.fit()
    failed = [r for r in grid if r.error is not None]
    if failed:
        raise RuntimeError(f"{len(failed)} trial lỗi sau {max_failures} lần thử lại: {failed[0].error!r}")
    best = grid.get_best_result(metric=METRIC, mode="min", scope="last")
    with best.checkpoint.as_directory() as folder:
        model = joblib.load(Path(folder) / MODEL_FILE)
    if model[-1].n_iter_ != rounds:
        raise RuntimeError(f"trial tốt nhất dừng ở {model[-1].n_iter_} cây, cần {rounds}")
    model.set_params(model__warm_start=False)
    X_valid, y_valid = build_features(valid)
    metrics = evaluate(model, X_valid, y_valid)
    params = {**dict(best.config), "max_iter": rounds}
    return Retrained(model=model, metrics=metrics, params=params, trials=len(grid))


def register(result: Retrained, config: Config, data_version: str) -> str:
    from mlflow import MlflowClient

    from eta.registry import log_and_register

    config.model_params = dict(result.params)
    metrics = {k: v for k, v in result.metrics.items() if not math.isnan(float(v))}
    version = log_and_register(result.model, metrics, config, data_version)
    client = MlflowClient(tracking_uri=config.mlflow_uri)
    client.set_model_version_tag(config.model_name, version, "trainer", "ray-tune")
    client.set_model_version_tag(config.model_name, version, "trials", str(result.trials))
    return version
