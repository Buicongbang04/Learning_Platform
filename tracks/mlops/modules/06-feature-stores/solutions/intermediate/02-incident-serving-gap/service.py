import pandas as pd

FEATURES = ["trip_distance", "hour", "is_weekend", "zone_id"]
KM_PER_MILE = 1.609344


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
        row = pd.DataFrame(
            [
                {
                    "pickup_ts": request["pickup_ts"],
                    "trip_distance": float(request["distance_km"]) / KM_PER_MILE,
                    "zone_id": request.get("zone_id"),
                }
            ]
        )
        return build_features(row)

    def predict(self, request: dict) -> float:
        return float(self.model.predict(self.featurize(request))[0])
