from pathlib import Path

import pandas as pd

PICKUP = "tpep_pickup_datetime"
DROPOFF = "tpep_dropoff_datetime"
TRIP_COLUMNS = [PICKUP, DROPOFF, "trip_distance", "PULocationID", "DOLocationID"]
MAX_MINUTES = 180
MAX_MILES = 100


def load_trips(path: str | Path, max_rows: int | None = None, seed: int = 0) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path, columns=TRIP_COLUMNS)
    else:
        df = pd.read_csv(path, usecols=TRIP_COLUMNS, parse_dates=[PICKUP, DROPOFF])
    if max_rows is not None and len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=seed).sort_index()
    return df.reset_index(drop=True)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    minutes = (df[DROPOFF] - df[PICKUP]).dt.total_seconds() / 60
    keep = (minutes > 0) & (minutes <= MAX_MINUTES) & (df["trip_distance"] > 0) & (df["trip_distance"] <= MAX_MILES)
    out = df.loc[keep].copy()
    out["duration_min"] = minutes[keep]
    return out.reset_index(drop=True)
