import subprocess
from pathlib import Path

import yaml
from mlflow import MlflowClient


def git_state(repo: Path) -> dict:
    """Trả {"commit": <sha đầy đủ 40 ký tự>, "dirty": <bool>} của repo tại `repo`.

    dirty = có thay đổi chưa commit ở tệp được theo dõi hoặc tệp mới chưa add.
    """
    # TODO: chạy `git -C <repo> rev-parse HEAD` và `git -C <repo> status --porcelain`
    raise NotImplementedError


def data_version_from_lock(lock_path: Path, stage: str) -> str:
    """Đọc dvc.lock, trả md5 của output đầu tiên của stage `stage`.

    Thiếu stage hoặc stage không có outs thì raise ValueError nêu tên stage.
    """
    # TODO: yaml.safe_load, đi tới stages[stage]["outs"][0]["md5"]
    raise NotImplementedError


def log_run(tracking_uri: str, experiment_id: str, params: dict, metrics: dict,
            repo: Path, lock_path: Path, stage: str) -> str:
    """Tạo một run FINISHED có params, metrics và tag lineage, trả run_id.

    Tag: git_commit, git_dirty ("true"/"false"), data_version.
    Dùng MlflowClient(tracking_uri), không đổi tracking URI toàn cục.
    """
    # TODO
    raise NotImplementedError


def find_runs(tracking_uri: str, experiment_id: str, data_version: str | None = None,
              git_commit: str | None = None) -> list[str]:
    """run_id của các run FINISHED khớp mọi điều kiện đã cho, run mới nhất đứng đầu.

    Không truyền điều kiện nào thì trả mọi run FINISHED.
    """
    # TODO: search_runs với filter_string trên tags.data_version / tags.git_commit
    raise NotImplementedError
