"""Chạy trong container Feast (không có package eta): chỉ import pandas và thư viện chuẩn ở đầu tệp."""

import pandas as pd

PUSH_SOURCE = "zone_speed_push"
REFS = ["zone_speed_15m:speed_15m_mph", "zone_speed_15m:trips"]


def to_push_frame(windows: list[dict]) -> pd.DataFrame:
    raise NotImplementedError("M16: DataFrame đúng cột cho push source")


def push(store, frame: pd.DataFrame) -> int:
    raise NotImplementedError("M16: offline mọi dòng, online dòng mới nhất mỗi zone nếu mới hơn")


def export_online(store, zones: list[int], path) -> int:
    raise NotImplementedError("M16: ghi snapshot online cho API (ghi tệp tạm rồi đổi tên)")
