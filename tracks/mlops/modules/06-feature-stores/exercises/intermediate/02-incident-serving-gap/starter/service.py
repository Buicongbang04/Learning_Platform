"""Dịch vụ dự đoán giá cước taxi: build_features (offline, dùng khi train) và FareService (online)."""
import pandas as pd

FEATURES = ["trip_distance", "hour", "is_weekend", "zone_id"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(df["pickup_ts"])
    return pd.DataFrame(
        {
            "trip_distance": df["trip_distance"].astype("float64"),
            "hour": ts.dt.hour.astype("float64"),
            "is_weekend": (ts.dt.dayofweek >= 5).astype("float64"),
            "zone_id": df["zone_id"].fillna(0).astype("float64"),
        },
        index=df.index,
    )[FEATURES]


class FareService:
    def __init__(self, model):
        self.model = model

    def featurize(self, request: dict) -> pd.DataFrame:
        if request.get("distance_km") is None:
            raise ValueError("thiếu distance_km")
        distance = float(request["distance_km"]) * 1.609344
        ts = pd.Timestamp(request["pickup_ts"])
        zone = request.get("zone_id")
        return pd.DataFrame(
            [
                {
                    "trip_distance": distance,
                    "hour": float(ts.hour),
                    "is_weekend": float(ts.dayofweek >= 5),
                    "zone_id": float(zone) if zone is not None else 0.0,
                }
            ]
        )[FEATURES]

    def predict(self, request: dict) -> float:
        return float(self.model.predict(self.featurize(request))[0])
