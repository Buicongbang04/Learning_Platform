import pandas as pd

from eta.clock import add_months
from eta.config import Config

LABEL_DELAY_MONTHS = 1


def published(month: str, as_of: str, delay: int = LABEL_DELAY_MONTHS) -> bool:
    return as_of >= add_months(month, delay)


def month_trips(month: str, config: Config) -> pd.DataFrame:
    from eta.data import load_month, month_path
    from eta.features import clean

    trips = clean(load_month(month_path(config.data_dir, month), config.sample_rows, config.seed), month)
    trips.insert(0, "request_id", [f"{month}-{i:07d}" for i in range(len(trips))])
    return trips


def labels_for(month: str, as_of: str, config: Config) -> pd.DataFrame | None:
    if not published(month, as_of):
        return None
    return month_trips(month, config)[["request_id", "duration_s"]]
