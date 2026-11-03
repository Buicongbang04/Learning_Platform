import pandas as pd
import pytest
from pandera.errors import SchemaErrors

from testkit import Exercise

ex = Exercise(__file__)
MONTH = "2019-01"


def clean_frame():
    pickups = pd.to_datetime(
        ["2019-01-01 00:00:05", "2019-01-15 12:30:00", "2019-01-31 23:59:59", "2019-01-10 08:00:00", "2019-01-20 18:45:00"]
    )
    return pd.DataFrame(
        {
            "tpep_pickup_datetime": pickups,
            "tpep_dropoff_datetime": pickups + pd.to_timedelta([300, 900, 600, 60, 1800], unit="s"),
            "trip_distance": [1.0, 2.5, 0.3, 12.0, 6.6],
            "PULocationID": [1, 100, 265, 50, 7],
            "DOLocationID": [2, 264, 1, 50, 265],
            "passenger_count": [1.0, None, 2.0, 1.0, 6.0],
        }
    )


def failing_rows(df):
    schema = ex.module("schema.py")
    with pytest.raises(SchemaErrors) as info:
        schema.validate_trips(df, MONTH)
    return set(info.value.failure_cases["index"].dropna().astype(int))


def test_clean_frame_passes_and_is_not_mutated():
    schema = ex.module("schema.py")
    df = clean_frame()
    before = df.copy()
    out = schema.validate_trips(df, MONTH)
    assert len(out) == 5
    pd.testing.assert_frame_equal(df, before)


def test_negative_and_zero_duration():
    df = clean_frame()
    df.loc[1, "tpep_dropoff_datetime"] = df.loc[1, "tpep_pickup_datetime"] - pd.Timedelta(seconds=30)
    df.loc[3, "tpep_dropoff_datetime"] = df.loc[3, "tpep_pickup_datetime"]
    assert failing_rows(df) == {1, 3}


def test_zero_distance():
    df = clean_frame()
    df.loc[2, "trip_distance"] = 0.0
    assert failing_rows(df) == {2}


def test_pickup_outside_month():
    df = clean_frame()
    for row, ts in ((0, "2008-12-31 23:00:00"), (4, "2018-12-31 22:10:00"), (1, "2019-02-01 00:00:00")):
        df.loc[row, "tpep_pickup_datetime"] = pd.Timestamp(ts)
        df.loc[row, "tpep_dropoff_datetime"] = pd.Timestamp(ts) + pd.Timedelta(minutes=10)
    assert failing_rows(df) == {0, 1, 4}


def test_zone_out_of_range():
    df = clean_frame()
    df.loc[0, "PULocationID"] = 0
    df.loc[3, "DOLocationID"] = 266
    assert failing_rows(df) == {0, 3}


def test_all_rules_reported_in_one_call():
    schema = ex.module("schema.py")
    df = clean_frame()
    df.loc[0, "trip_distance"] = 0.0
    df.loc[1, "PULocationID"] = 999
    df.loc[2, "tpep_dropoff_datetime"] = df.loc[2, "tpep_pickup_datetime"] - pd.Timedelta(minutes=1)
    df.loc[3, "tpep_pickup_datetime"] = pd.Timestamp("2008-01-01")
    df.loc[3, "tpep_dropoff_datetime"] = pd.Timestamp("2008-01-01 00:10:00")
    with pytest.raises(SchemaErrors) as info:
        schema.validate_trips(df, MONTH)
    assert set(info.value.failure_cases["index"].dropna().astype(int)) == {0, 1, 2, 3}


def test_coerces_narrow_dtypes():
    schema = ex.module("schema.py")
    df = clean_frame().astype({"PULocationID": "int32", "DOLocationID": "int16", "trip_distance": "float32"})
    schema.validate_trips(df, MONTH)
