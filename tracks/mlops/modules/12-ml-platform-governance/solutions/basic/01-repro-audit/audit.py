import re
from mlflow import MlflowClient

SHA1 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
MOVING = {"", "unknown", "none", "latest", "n/a"}


def _commit_ok(run) -> bool:
    tags = run.data.tags
    return bool(SHA1.fullmatch(tags.get("git_commit", ""))) and tags.get("git_dirty") == "false"


def _data_ok(run) -> bool:
    return run.data.tags.get("data_version", "").strip().lower() not in MOVING


def _lock_ok(run) -> bool:
    return bool(SHA256.fullmatch(run.data.tags.get("lockfile_sha256", "")))


def _seed_ok(run) -> bool:
    try:
        int(run.data.params["seed"])
    except (KeyError, ValueError):
        return False
    return True


CHECKS = (("commit", _commit_ok), ("data_version", _data_ok), ("lockfile_hash", _lock_ok), ("seed", _seed_ok))


def audit_run(tracking_uri: str, run_id: str) -> list[str]:
    run = MlflowClient(tracking_uri).get_run(run_id)
    return [name for name, check in CHECKS if not check(run)]


def run_of_version(tracking_uri: str, model_name: str, version: int) -> str:
    try:
        run_id = MlflowClient(tracking_uri).get_model_version(model_name, str(version)).run_id
    except Exception as exc:
        raise LookupError(f"{model_name} v{version} không tồn tại") from exc
    if not run_id:
        raise LookupError(f"{model_name} v{version} không có run nguồn")
    return run_id


def audit_model(tracking_uri: str, model_name: str, version: int) -> dict:
    run_id = run_of_version(tracking_uri, model_name, version)
    missing = audit_run(tracking_uri, run_id)
    return {"run_id": run_id, "missing": missing, "reproducible": not missing}
