import pandas as pd

DEFAULT_SPEED_MPH = None
MIN_TRIPS = 5


def zone_hour_speed(df: pd.DataFrame, month: str) -> pd.DataFrame:
    raise NotImplementedError("M06: bảng PULocationID, pickup_hour, avg_speed_mph, event_timestamp (đầu tháng sau)")


def attach_speed(trips: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("M06: point-in-time bằng merge_asof, TTL 62 ngày, thiếu thì DEFAULT_SPEED_MPH")
