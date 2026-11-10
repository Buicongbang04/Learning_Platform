import time

import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException


def register_version(client: MlflowClient, model_name: str, model_uri: str, model_id: str,
                     run_id: str, tags: dict | None = None) -> int:
    try:
        client.create_registered_model(model_name)
    except MlflowException as error:
        if "RESOURCE_ALREADY_EXISTS" not in str(error) and "already exists" not in str(error):
            raise
    version = client.create_model_version(model_name, model_uri, run_id, tags=tags, model_id=model_id)
    deadline = time.time() + 60
    while version.status != "READY":
        if version.status == "FAILED_REGISTRATION" or time.time() > deadline:
            raise RuntimeError(f"version {version.version} không READY: {version.status}")
        time.sleep(0.5)
        version = client.get_model_version(model_name, version.version)
    return int(version.version)


def _holder(client: MlflowClient, model_name: str, alias: str) -> int | None:
    try:
        return int(client.get_model_version_by_alias(model_name, alias).version)
    except MlflowException:
        return None


def promote(client: MlflowClient, model_name: str, version: int, alias: str = "champion") -> int | None:
    previous = _holder(client, model_name, alias)
    if previous is not None and previous != int(version):
        client.set_model_version_tag(model_name, str(version), f"previous_{alias}", str(previous))
    client.set_registered_model_alias(model_name, alias, str(version))
    return previous


def rollback(client: MlflowClient, model_name: str, alias: str = "champion") -> int:
    current = _holder(client, model_name, alias)
    if current is None:
        raise LookupError(f"alias '{alias}' chưa tồn tại trên {model_name}")
    tags = client.get_model_version(model_name, str(current)).tags
    target = tags.get(f"previous_{alias}")
    if not target:
        raise LookupError(f"version {current} không có đường lui (thiếu tag previous_{alias})")
    client.set_registered_model_alias(model_name, alias, target)
    client.set_model_version_tag(model_name, str(current), "rolled_back", "true")
    return int(target)


def load_by_alias(client: MlflowClient, model_name: str, alias: str = "champion"):
    version = int(client.get_model_version_by_alias(model_name, alias).version)
    return mlflow.pyfunc.load_model(f"models:/{model_name}/{version}"), version
