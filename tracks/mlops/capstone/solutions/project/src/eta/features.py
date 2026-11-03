import pandas as pd

from eta.data import COLUMNS

FEATURES = ["PULocationID", "DOLocationID", "pickup_hour", "pickup_dow", "trip_distance"]
OPTIONAL_FEATURES = ["avg_speed_mph"]
TARGET = "duration_s"
AIRPORT_ZONES = (132, 138)
MIN_DURATION_S = 60
MAX_DURATION_S = 10_800
MAX_DISTANCE = 100
MAX_ZONE = 263


def month_bounds(month: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(f"{month}-01")
    return start, start + pd.offsets.MonthBegin(1)


def clean(df: pd.DataFrame, month: str) -> pd.DataFrame:
    duration = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds()
    start, end = month_bounds(month)
    pickup = df["tpep_pickup_datetime"]
    keep = (
        duration.between(MIN_DURATION_S, MAX_DURATION_S)
        & (df["trip_distance"] > 0)
        & (df["trip_distance"] <= MAX_DISTANCE)
        & (pickup >= start)
        & (pickup < end)
        & df["PULocationID"].between(1, MAX_ZONE)
        & df["DOLocationID"].between(1, MAX_ZONE)
    )
    out = df.loc[keep, COLUMNS].copy()
    out[TARGET] = duration[keep]
    return out.reset_index(drop=True)


def feature_columns(df: pd.DataFrame) -> list[str]:
    return FEATURES + [c for c in OPTIONAL_FEATURES if c in df.columns]


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    pickup = pd.to_datetime(df["tpep_pickup_datetime"])
    columns = {
        "PULocationID": df["PULocationID"].astype("int64").to_numpy(),
        "DOLocationID": df["DOLocationID"].astype("int64").to_numpy(),
        "pickup_hour": pickup.dt.hour.astype("int64").to_numpy(),
        "pickup_dow": pickup.dt.day_of_week.astype("int64").to_numpy(),
        "trip_distance": df["trip_distance"].astype("float64").to_numpy(),
    }
    for name in OPTIONAL_FEATURES:
        if name in df.columns:
            columns[name] = df[name].astype("float64").to_numpy()
    return pd.DataFrame(columns, index=df.index)[feature_columns(df)]


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return make_features(df), df[TARGET].astype("float64")
