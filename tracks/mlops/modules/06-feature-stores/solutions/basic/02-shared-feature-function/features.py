import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["hour_sin", "hour_cos", "is_night", "is_weekend", "zone_id", "zone_known", "trip_distance"]
DEFAULT_DISTANCE = 1.5


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(df["pickup_ts"])
    hour = ts.dt.hour.to_numpy(dtype="float64")
    zone = pd.to_numeric(df["zone_id"], errors="coerce")
    known = zone.between(1, 265)
    distance = pd.to_numeric(df["trip_distance"], errors="coerce").fillna(DEFAULT_DISTANCE).clip(lower=0.0)
    out = pd.DataFrame(
        {
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "is_night": ((hour >= 22) | (hour < 6)).astype("float64"),
            "is_weekend": (ts.dt.dayofweek.to_numpy() >= 5).astype("float64"),
            "zone_id": zone.where(known, 0).astype("float64").to_numpy(),
            "zone_known": known.astype("float64").to_numpy(),
            "trip_distance": distance.astype("float64").to_numpy(),
        },
        index=df.index,
    )
    return out[FEATURE_COLUMNS]


def train_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return compute_features(df)


def serve_one(request: dict) -> dict:
    if request.get("pickup_ts") is None:
        raise ValueError("thiếu pickup_ts")
    frame = pd.DataFrame(
        [{"pickup_ts": request["pickup_ts"], "zone_id": request.get("zone_id"), "trip_distance": request.get("trip_distance")}]
    )
    return {k: float(v) for k, v in compute_features(frame).iloc[0].items()}
