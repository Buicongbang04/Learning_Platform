"""Point-in-time join tự viết bằng pd.merge_asof."""
import pandas as pd


def point_in_time_join(
    events: pd.DataFrame,
    features: pd.DataFrame,
    key: str,
    event_ts: str = "event_ts",
    feature_ts: str = "feature_ts",
    tolerance: pd.Timedelta | None = None,
) -> pd.DataFrame:
    raise NotImplementedError("TODO: nối mỗi sự kiện với bản ghi feature mới nhất không muộn hơn thời điểm sự kiện")
