from pathlib import Path

import pandas as pd

COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]


def load_month(path: Path, sample_rows: int | None, seed: int) -> pd.DataFrame:
    raise NotImplementedError("M01: chỉ đọc COLUMNS, lấy mẫu xác định theo seed")
