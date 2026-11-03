import json
from pathlib import Path

import joblib
import pandas as pd
from prefect import flow, task
from sklearn.linear_model import LinearRegression


def month_range(start: str, end: str) -> list[str]:
    """Các tháng 'YYYY-MM' từ start đến end, gồm cả hai đầu. Sai định dạng hoặc start > end: ValueError."""
    # TODO
    raise NotImplementedError


def train_month(month: str, data_dir, out_dir, seed: int = 0) -> dict:
    """Đọc data_dir/trips-<month>.csv, fit LinearRegression(distance_km -> duration_s).

    Ghi out_dir/model-<month>.joblib và out_dir/model-<month>.json
    {"month", "rows", "mae", "data_sha256"} (sha256 của tệp CSV nguồn). Trả dict metadata.
    Lỗi giữa chừng không để lại tệp dở dang cho tháng đó.
    """
    # TODO
    raise NotImplementedError


def backfill(start: str, end: str, data_dir, out_dir, overwrite: bool = False) -> dict:
    """Chạy các tháng start..end. Trả {"done": [...], "skipped": [...], "failed": {tháng: thông báo lỗi}}.

    Tháng đã có cả hai tệp đầu ra thì skipped, trừ khi overwrite=True. Một tháng lỗi không dừng các tháng còn lại.
    """
    # TODO
    raise NotImplementedError
