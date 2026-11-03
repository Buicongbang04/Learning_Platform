"""Đẩy feature cửa sổ vào Feast qua push source; chạy trong container Feast, phần dựng DataFrame chạy được cả trên máy."""

import pandas as pd

PUSH_SOURCE = "zone_window_push"
REFS = ["zone_window:trips", "zone_window:avg_fare"]


def to_push_frame(windows: list[dict]) -> pd.DataFrame:
    raise NotImplementedError("TODO 5: DataFrame zone_id, trips, avg_fare, event_timestamp")


def push(store, frame: pd.DataFrame) -> int:
    raise NotImplementedError("TODO 6: ghi offline mọi dòng, ghi online dòng mới nhất mỗi zone; trả số dòng ghi online")
