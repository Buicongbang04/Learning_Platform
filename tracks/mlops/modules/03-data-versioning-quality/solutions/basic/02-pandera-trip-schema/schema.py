import pandas as pd
import pandera.pandas as pa


def trip_schema(month: str) -> pa.DataFrameSchema:
    start = pd.Timestamp(month + "-01")
    end = start + pd.offsets.MonthBegin(1)
    zone = pa.Column(int, pa.Check.in_range(1, 265), coerce=True)
    return pa.DataFrameSchema(
        {
            "tpep_pickup_datetime": pa.Column(
                "datetime64[ns]",
                pa.Check(lambda s: (s >= start) & (s < end), name="pickup_in_month"),
                coerce=True,
            ),
            "tpep_dropoff_datetime": pa.Column("datetime64[ns]", coerce=True),
            "trip_distance": pa.Column(float, pa.Check.gt(0), coerce=True),
            "PULocationID": zone,
            "DOLocationID": zone,
            "passenger_count": pa.Column(float, nullable=True, coerce=True),
        },
        checks=pa.Check(
            lambda df: df["tpep_dropoff_datetime"] > df["tpep_pickup_datetime"], name="positive_duration"
        ),
    )


def validate_trips(df: pd.DataFrame, month: str) -> pd.DataFrame:
    return trip_schema(month).validate(df, lazy=True)
