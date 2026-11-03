import pandas as pd
import pandera.pandas as pa

from eta.features import month_bounds

MAX_BAD_SHARE = 0.01


def _share_at_most(name: str, bad, limit: float = MAX_BAD_SHARE) -> pa.Check:
    return pa.Check(lambda df: bool(bad(df).mean() <= limit), name=name, error=f"{name} > {limit:.0%}")


ZONE = pa.Check.in_range(1, 265)

SCHEMA = pa.DataFrameSchema(
    columns={
        "tpep_pickup_datetime": pa.Column(pa.DateTime, nullable=False),
        "tpep_dropoff_datetime": pa.Column(pa.DateTime, nullable=False),
        "PULocationID": pa.Column("int64", ZONE, nullable=False),
        "DOLocationID": pa.Column("int64", ZONE, nullable=False),
        "trip_distance": pa.Column("float64", nullable=False),
    },
    checks=[
        pa.Check(lambda df: len(df) > 0, name="not_empty", error="không có dòng nào"),
        _share_at_most("negative_duration_share", lambda df: df["tpep_dropoff_datetime"] < df["tpep_pickup_datetime"]),
        _share_at_most("negative_distance_share", lambda df: df["trip_distance"] < 0),
    ],
    strict=True,
)


def schema_for(month: str) -> pa.DataFrameSchema:
    start, end = month_bounds(month)
    outside = _share_at_most(
        "pickup_outside_month_share",
        lambda df: (df["tpep_pickup_datetime"] < start) | (df["tpep_pickup_datetime"] >= end),
    )
    return pa.DataFrameSchema(columns=SCHEMA.columns, checks=[*SCHEMA.checks, outside], strict=SCHEMA.strict)


def validate_month(df: pd.DataFrame, month: str) -> None:
    schema_for(month).validate(df, lazy=True)
