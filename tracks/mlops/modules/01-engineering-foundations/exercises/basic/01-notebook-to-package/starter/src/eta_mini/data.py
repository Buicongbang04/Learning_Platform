from pathlib import Path

import pandas as pd

PICKUP = "tpep_pickup_datetime"
DROPOFF = "tpep_dropoff_datetime"
TRIP_COLUMNS = [PICKUP, DROPOFF, "trip_distance", "PULocationID", "DOLocationID"]
MAX_MINUTES = 180
MAX_MILES = 100


def load_trips(path: str | Path, max_rows: int | None = None, seed: int = 0) -> pd.DataFrame:
    # TODO: đọc .parquet hoặc .csv (theo đuôi tệp), chỉ đọc TRIP_COLUMNS; nếu max_rows nhỏ hơn số dòng thì lấy mẫu theo seed
    raise NotImplementedError


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: thêm cột duration_min; giữ chuyến có 0 < duration_min <= MAX_MINUTES và 0 < trip_distance <= MAX_MILES
    raise NotImplementedError
