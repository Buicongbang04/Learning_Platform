import hashlib
import json
from pathlib import Path

from prefect import flow, task


def file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def count_rows(path: str) -> int:
    with open(path, encoding="utf-8") as handle:
        return max(sum(1 for line in handle if line.strip()) - 1, 0)


def read_state(state_path: str) -> dict | None:
    path = Path(state_path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


@task
def run_training(train_fn, data_path: str) -> dict:
    return train_fn(data_path)


@flow(validate_parameters=False)
def ct_flow(data_path: str, state_path: str, train_fn, min_new_rows: int = 0, force: bool = False) -> dict:
    digest = file_sha256(data_path)
    rows = count_rows(data_path)
    if rows == 0:
        raise ValueError(f"{data_path} không có dòng dữ liệu nào")
    state = read_state(state_path)
    if state is not None and not force:
        if state["last_data_sha256"] == digest:
            return {"status": "skipped", "reason": "unchanged"}
        if rows - state["rows"] < min_new_rows:
            return {"status": "skipped", "reason": "too_few_new_rows"}
    run_training(train_fn, data_path)
    Path(state_path).write_text(json.dumps({"last_data_sha256": digest, "rows": rows}), encoding="utf-8")
    return {"status": "trained", "data_sha256": digest}
