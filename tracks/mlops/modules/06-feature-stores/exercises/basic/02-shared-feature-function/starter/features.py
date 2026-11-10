"""Một hàm tính feature dùng chung cho train (batch) và serve (từng yêu cầu)."""
import pandas as pd

FEATURE_COLUMNS = ["hour_sin", "hour_cos", "is_night", "is_weekend", "zone_id", "zone_known", "trip_distance"]
DEFAULT_DISTANCE = 1.5


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("TODO: tính FEATURE_COLUMNS từ pickup_ts, zone_id, trip_distance")


def train_matrix(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("TODO: ma trận feature cho train, dùng compute_features")


def serve_one(request: dict) -> dict:
    raise NotImplementedError("TODO: feature cho một yêu cầu, dùng compute_features")
