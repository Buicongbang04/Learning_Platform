import hashlib
import json
from pathlib import Path

from prefect import flow


def file_sha256(path: str) -> str:
    """sha256 của các byte trong tệp."""
    # TODO
    raise NotImplementedError


@flow(validate_parameters=False)
def ct_flow(data_path: str, state_path: str, train_fn, min_new_rows: int = 0, force: bool = False) -> dict:
    """Trigger "có dữ liệu mới" cho continuous training.

    state_path là JSON {"last_data_sha256": ..., "rows": ...} của lần train thành công gần nhất.
    Trả {"status": "trained", "data_sha256": ...} hoặc {"status": "skipped", "reason": "unchanged" | "too_few_new_rows"}.
    """
    # TODO
    raise NotImplementedError
