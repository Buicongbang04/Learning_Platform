"""Ghi và tìm lại thí nghiệm bằng MLflow Tracking, với backend SQLite tự chỉ định."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from mlflow import MlflowClient


def get_or_create_experiment(tracking_uri: str, name: str, artifact_root: str | Path) -> str:
    """Trả experiment_id của experiment `name`; tạo mới nếu chưa có.

    Khi tạo mới, đặt artifact_location bên trong `artifact_root` (ví dụ artifact_root / name),
    để artifact không rơi vào ./mlruns của thư mục đang chạy.
    """
    # TODO: client = MlflowClient(tracking_uri); get_experiment_by_name; create_experiment(..., artifact_location=...)
    raise NotImplementedError


def log_training_run(tracking_uri: str, experiment_id: str, params: dict, metrics: dict,
                     tags: dict | None = None) -> str:
    """Tạo một run, ghi params, metrics, tags, kết thúc run với status FINISHED. Trả run_id.

    Giá trị metric là một số, hoặc một list số: khi đó phần tử thứ i được ghi ở step i
    (ví dụ val_auc qua từng epoch).
    """
    # TODO: client.create_run(experiment_id, tags=...), log_param / log_metric(..., step=i), set_terminated
    raise NotImplementedError


def best_run(tracking_uri: str, experiment_id: str, metric: str, higher_is_better: bool = True) -> dict:
    """Run tốt nhất theo `metric` trong các run đã FINISHED và có ghi metric đó.

    Trả {"run_id": str, "params": dict[str, str], "value": float}. Không có run phù hợp thì ValueError.
    """
    # TODO: client.search_runs(..., filter_string=..., order_by=[...], max_results=1)
    raise NotImplementedError
