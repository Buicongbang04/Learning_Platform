"""Xuất metric pipeline theo Prometheus text exposition format."""

from __future__ import annotations

from datetime import datetime

FAMILIES = [
    # (tên metric, loại, help, khoá trong dict stats)
    ("pipeline_rows_processed_total", "counter", "Rows processed by the pipeline.", "rows_processed"),
    ("pipeline_last_success_timestamp_seconds", "gauge", "Unix time of the last successful run.", "last_success"),
    ("pipeline_duration_seconds", "gauge", "Duration of the last run in seconds.", "duration_seconds"),
]


def escape_label_value(value: str) -> str:
    # TODO 1: thoát \ thành \\, " thành \", xuống dòng thành \n
    raise NotImplementedError


def render_metrics(stats: list[dict]) -> str:
    # TODO 2: với mỗi family: dòng # HELP, dòng # TYPE, rồi một dòng mẫu cho mỗi pipeline
    raise NotImplementedError


def freshness_seconds(now: float | datetime, last_success: float | datetime | None) -> float:
    # TODO 3: None -> inf; datetime -> .timestamp(); kết quả không âm
    raise NotImplementedError
