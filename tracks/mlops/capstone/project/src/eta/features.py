import pandas as pd

FEATURES = ["PULocationID", "DOLocationID", "pickup_hour", "pickup_dow", "trip_distance"]


def clean(df: pd.DataFrame, month: str) -> pd.DataFrame:
    raise NotImplementedError("M01: luật làm sạch cố định, thêm cột duration_s")


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    raise NotImplementedError("M01: trả (X[FEATURES], y = duration_s)")
