from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]


def month_path(data_dir: Path, month: str) -> Path:
    return Path(data_dir) / f"yellow_tripdata_{month}.parquet"


def load_month(path: Path, sample_rows: int | None, seed: int) -> pd.DataFrame:
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=COLUMNS)
    if sample_rows is not None and sample_rows < table.num_rows:
        rng = np.random.default_rng(seed)
        table = table.take(np.sort(rng.choice(table.num_rows, size=sample_rows, replace=False)))
    return table.to_pandas()[COLUMNS]
