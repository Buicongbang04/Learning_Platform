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
    client = MlflowClient(tracking_uri)
    existing = client.get_experiment_by_name(name)
    if existing is not None:
        return existing.experiment_id
    location = (Path(artifact_root) / name).resolve()
    return client.create_experiment(name, artifact_location=location.as_uri())


def log_training_run(tracking_uri: str, experiment_id: str, params: dict, metrics: dict,
                     tags: dict | None = None) -> str:
    """Tạo một run, ghi params, metrics, tags, kết thúc run với status FINISHED. Trả run_id.

    Giá trị metric là một số, hoặc một list số: khi đó phần tử thứ i được ghi ở step i
    (ví dụ val_auc qua từng epoch).
    """
    client = MlflowClient(tracking_uri)
    run_id = client.create_run(experiment_id, tags=tags or {}).info.run_id
    try:
        for key, value in params.items():
            client.log_param(run_id, key, value)
        for key, value in metrics.items():
            values = value if isinstance(value, (list, tuple)) else [value]
            for step, v in enumerate(values):
                client.log_metric(run_id, key, float(v), step=step)
    except Exception:
        client.set_terminated(run_id, status="FAILED")
        raise
    client.set_terminated(run_id, status="FINISHED")
    return run_id


def best_run(tracking_uri: str, experiment_id: str, metric: str, higher_is_better: bool = True) -> dict:
    """Run tốt nhất theo `metric` trong các run đã FINISHED và có ghi metric đó.

    Trả {"run_id": str, "params": dict[str, str], "value": float}. Không có run phù hợp thì ValueError.
    """
    client = MlflowClient(tracking_uri)
    order = "DESC" if higher_is_better else "ASC"
    runs = client.search_runs(
        [experiment_id],
        filter_string=f"attributes.status = 'FINISHED' and metrics.{metric} > -1e308",
        order_by=[f"metrics.{metric} {order}"],
        max_results=1,
    )
    if not runs:
        raise ValueError(f"Không có run FINISHED nào ghi metric {metric!r}")
    run = runs[0]
    return {"run_id": run.info.run_id, "params": dict(run.data.params), "value": run.data.metrics[metric]}
