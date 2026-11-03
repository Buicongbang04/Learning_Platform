import json

from mlflow import MlflowClient
from mlflow.exceptions import MlflowException


def _run(client: MlflowClient, model_name: str, version: int):
    return client.get_run(client.get_model_version(model_name, str(version)).run_id)


def collect_metrics(client: MlflowClient, model_name: str, version: int) -> dict:
    metrics = _run(client, model_name, version).data.metrics
    slices = {}
    for key, value in metrics.items():
        if key.startswith("mae_slice."):
            name = key.removeprefix("mae_slice.")
            slices[name] = {"mae": value, "n": int(metrics.get(f"n_slice.{name}", 0))}
    return {"mae": metrics["mae"], "latency_p95_ms": metrics["latency_p95_ms"], "slices": slices}


def lineage_problems(client: MlflowClient, model_name: str, version: int) -> list[str]:
    tags = _run(client, model_name, version).data.tags
    problems = []
    if tags.get("git_dirty") == "true":
        problems.append("lineage: train từ cây thư mục bẩn (git_dirty=true)")
    for name in ("data_version", "git_commit"):
        if not tags.get(name):
            problems.append(f"lineage: thiếu tag {name}")
    return problems


def _holder(client: MlflowClient, model_name: str, alias: str) -> int | None:
    try:
        return int(client.get_model_version_by_alias(model_name, alias).version)
    except MlflowException:
        return None


def gate_and_promote(client: MlflowClient, model_name: str, challenger_version: int, decide,
                     policy: dict | None = None, alias: str = "champion") -> dict:
    champion_version = _holder(client, model_name, alias)
    if champion_version == int(challenger_version):
        raise ValueError(f"version {challenger_version} đã giữ alias {alias}")
    challenger = collect_metrics(client, model_name, challenger_version)
    champion = collect_metrics(client, model_name, champion_version) if champion_version is not None else None
    decision = decide(challenger, champion, policy)
    reasons = list(decision.reasons) + lineage_problems(client, model_name, challenger_version)
    promoted = bool(decision.promote) and not any(r.startswith("lineage:") for r in reasons)
    version = str(challenger_version)
    client.set_model_version_tag(model_name, version, "promotion.decision", "promoted" if promoted else "rejected")
    client.set_model_version_tag(model_name, version, "promotion.reasons", json.dumps(reasons, ensure_ascii=False))
    client.set_model_version_tag(model_name, version, "promotion.compared_to",
                                 str(champion_version) if champion_version is not None else "none")
    if promoted:
        if champion_version is not None:
            client.set_model_version_tag(model_name, version, f"previous_{alias}", str(champion_version))
            client.set_model_version_tag(model_name, str(champion_version), "superseded_by", version)
        client.set_registered_model_alias(model_name, alias, version)
    return {"promoted": promoted, "reasons": reasons, "version": int(challenger_version)}
