import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from mlflow import MlflowClient

TRAINER = Path(__file__).with_name("trainer.py")
REQUIREMENTS = "scalekit>=1.4\n"


def choose(index: dict, name: str) -> str:
    return max(index[name], key=lambda v: tuple(int(p) for p in v.split(".")))


def run_trainer(path: Path, workdir: Path, seed: int, alpha: float) -> list[float]:
    out = Path(workdir) / "preds.json"
    env = {**os.environ, "PYTHONPATH": str(path)}
    subprocess.run([sys.executable, str(TRAINER), str(seed), str(alpha), str(out)], env=env, check=True)
    return json.loads(out.read_text(encoding="utf-8"))


def installed_version(path: Path) -> str:
    env = {**os.environ, "PYTHONPATH": str(path)}
    done = subprocess.run(
        [sys.executable, "-c", "import scalekit; print(scalekit.__version__)"],
        env=env, capture_output=True, text=True, check=True,
    )
    return done.stdout.strip()


def train_and_log(tracking_uri: str, experiment_id: str, workdir: Path, index: dict, seed: int = 7, alpha: float = 1.0) -> str:
    client = MlflowClient(tracking_uri)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    version = choose(index, "scalekit")
    path = index["scalekit"][version]
    lock = f"scalekit=={installed_version(path)}\n"
    tags = {
        "git_commit": "c" * 40,
        "git_dirty": "false",
        "data_version": "synthetic-t3-v1",
        "lockfile_sha256": hashlib.sha256(lock.encode("utf-8")).hexdigest(),
    }
    run = client.create_run(experiment_id, tags=tags)
    run_id = run.info.run_id
    try:
        client.log_param(run_id, "seed", str(seed))
        client.log_param(run_id, "alpha", str(alpha))
        preds = run_trainer(path, workdir, seed, alpha)
        (workdir / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
        (workdir / "requirements.lock").write_bytes(lock.encode("utf-8"))
        client.log_artifact(run_id, str(workdir / "requirements.txt"))
        client.log_artifact(run_id, str(workdir / "requirements.lock"))
        client.log_artifact(run_id, str(workdir / "preds.json"))
        client.log_metric(run_id, "holdout_mean", sum(preds) / len(preds))
    except Exception:
        client.set_terminated(run_id, status="FAILED")
        raise
    client.set_terminated(run_id, status="FINISHED")
    return run_id


def replay(tracking_uri: str, run_id: str, workdir: Path, index: dict) -> list[float]:
    client = MlflowClient(tracking_uri)
    run = client.get_run(run_id)
    seed, alpha = int(run.data.params["seed"]), float(run.data.params["alpha"])
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    if "requirements.lock" not in {a.path for a in client.list_artifacts(run_id)}:
        raise LookupError(f"run {run_id} không có artifact requirements.lock: không biết bản thư viện đã chạy lúc train")
    lock_path = client.download_artifacts(run_id, "requirements.lock", str(workdir))
    lock = Path(lock_path).read_bytes()
    if hashlib.sha256(lock).hexdigest() != run.data.tags.get("lockfile_sha256"):
        raise LookupError(f"requirements.lock của run {run_id} không khớp tag lockfile_sha256: không tin được bản ghim")
    pinned = {}
    for line in lock.decode("utf-8").split():
        name, _, version = line.partition("==")
        pinned[name] = version
    if "scalekit" not in pinned:
        raise LookupError("requirements.lock không ghim scalekit")
    for name, version in pinned.items():
        if version not in index.get(name, {}):
            raise LookupError(f"không còn {name}=={version} trong index")
    return run_trainer(index["scalekit"][pinned["scalekit"]], workdir, seed, alpha)
