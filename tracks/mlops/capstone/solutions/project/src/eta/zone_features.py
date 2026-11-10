import pandas as pd

from eta.features import month_bounds

SPEED_FEATURE = "avg_speed_mph"
SPEED_COLUMNS = ["PULocationID", "pickup_hour", SPEED_FEATURE, "event_timestamp"]
DEFAULT_SPEED_MPH = 10.1
MIN_TRIPS = 5
TTL = pd.Timedelta(days=62)
KEYS = ["PULocationID", "pickup_hour"]


class MissingSpeedTable(RuntimeError):
    pass


def needs_speed(model) -> bool:
    return SPEED_FEATURE in getattr(model, "feature_names_in_", ())


def read_speed_table(path) -> pd.DataFrame:
    path = str(path)
    table = pd.read_csv(path) if path.endswith(".csv") else pd.read_parquet(path)
    table["event_timestamp"] = pd.to_datetime(table["event_timestamp"])
    return table[SPEED_COLUMNS]


def prepare(frame: pd.DataFrame, model, table: pd.DataFrame | None) -> pd.DataFrame:
    if not needs_speed(model):
        return frame
    if table is None:
        raise MissingSpeedTable(f"model cần {SPEED_FEATURE} nhưng chưa cấu hình bảng feature (speed_table / ETA_SPEED_TABLE)")
    return attach_speed(frame, table)


def zone_hour_speed(df: pd.DataFrame, month: str) -> pd.DataFrame:
    speed = df["trip_distance"] / (df["duration_s"] / 3600)
    frame = pd.DataFrame({"PULocationID": df["PULocationID"].astype("int64"),
                          "pickup_hour": df["tpep_pickup_datetime"].dt.hour.astype("int64"), SPEED_FEATURE: speed})
    groups = frame.groupby(KEYS)[SPEED_FEATURE].agg(["median", "size"])
    table = groups[groups["size"] >= MIN_TRIPS]["median"].rename(SPEED_FEATURE).reset_index()
    table[SPEED_FEATURE] = table[SPEED_FEATURE].astype("float64")
    table["event_timestamp"] = month_bounds(month)[1]
    table["event_timestamp"] = table["event_timestamp"].astype("datetime64[us]")
    return table[SPEED_COLUMNS]


def attach_speed(trips: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    pickup = pd.to_datetime(trips["tpep_pickup_datetime"]).astype("datetime64[us]")
    left = pd.DataFrame({"_row": range(len(trips)), "_ts": pickup.to_numpy(),
                         "PULocationID": trips["PULocationID"].astype("int64").to_numpy(),
                         "pickup_hour": pickup.dt.hour.astype("int64").to_numpy()})
    right = features[SPEED_COLUMNS].rename(columns={"event_timestamp": "_ts"}).copy()
    right["_ts"] = pd.to_datetime(right["_ts"]).astype("datetime64[us]")
    right["PULocationID"] = right["PULocationID"].astype("int64")
    right["pickup_hour"] = right["pickup_hour"].astype("int64")
    merged = pd.merge_asof(left.sort_values("_ts", kind="mergesort"), right.sort_values("_ts", kind="mergesort"),
                           on="_ts", by=KEYS, direction="backward", allow_exact_matches=True, tolerance=TTL)
    speed = merged.sort_values("_row")[SPEED_FEATURE].fillna(DEFAULT_SPEED_MPH).to_numpy()
    out = trips.copy()
    out[SPEED_FEATURE] = speed
    return out
