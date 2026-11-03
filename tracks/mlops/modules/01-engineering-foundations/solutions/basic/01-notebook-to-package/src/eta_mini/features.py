import pandas as pd

from eta_mini.data import PICKUP

FEATURES = ["trip_distance", "hour", "dow", "PULocationID", "DOLocationID"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "trip_distance": df["trip_distance"].astype(float),
            "hour": df[PICKUP].dt.hour,
            "dow": df[PICKUP].dt.dayofweek,
            "PULocationID": df["PULocationID"],
            "DOLocationID": df["DOLocationID"],
        }
    )
    return frame[FEATURES]
