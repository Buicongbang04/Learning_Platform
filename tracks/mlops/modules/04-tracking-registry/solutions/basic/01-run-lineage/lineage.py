import subprocess
from pathlib import Path

import yaml
from mlflow import MlflowClient


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def git_state(repo: Path) -> dict:
    commit = _git(repo, "rev-parse", "HEAD").strip()
    dirty = bool(_git(repo, "status", "--porcelain").strip())
    return {"commit": commit, "dirty": dirty}


def data_version_from_lock(lock_path: Path, stage: str) -> str:
    lock = yaml.safe_load(Path(lock_path).read_text(encoding="utf-8")) or {}
    outs = (lock.get("stages") or {}).get(stage, {}).get("outs") or []
    if not outs:
        raise ValueError(f"dvc.lock không có output cho stage '{stage}'")
    return outs[0]["md5"]


def log_run(tracking_uri: str, experiment_id: str, params: dict, metrics: dict,
            repo: Path, lock_path: Path, stage: str) -> str:
    client = MlflowClient(tracking_uri)
    state = git_state(repo)
    tags = {
        "git_commit": state["commit"],
        "git_dirty": "true" if state["dirty"] else "false",
        "data_version": data_version_from_lock(lock_path, stage),
    }
    run = client.create_run(experiment_id, tags=tags)
    run_id = run.info.run_id
    try:
        for key, value in params.items():
            client.log_param(run_id, key, value)
        for key, value in metrics.items():
            client.log_metric(run_id, key, value)
    except Exception:
        client.set_terminated(run_id, status="FAILED")
        raise
    client.set_terminated(run_id, status="FINISHED")
    return run_id


def find_runs(tracking_uri: str, experiment_id: str, data_version: str | None = None,
              git_commit: str | None = None) -> list[str]:
    conditions = ["attributes.status = 'FINISHED'"]
    if data_version is not None:
        conditions.append(f"tags.data_version = '{data_version}'")
    if git_commit is not None:
        conditions.append(f"tags.git_commit = '{git_commit}'")
    runs = MlflowClient(tracking_uri).search_runs(
        [experiment_id], filter_string=" and ".join(conditions), order_by=["attributes.start_time DESC"])
    return [run.info.run_id for run in runs]
