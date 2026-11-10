import pandas as pd
import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def join():
    return ex.module("pit.py").point_in_time_join


def ts(text):
    return pd.Timestamp(text)


@pytest.fixture
def small():
    features = pd.DataFrame(
        {
            "zone": [1, 1, 1, 2, 2],
            "feature_ts": [ts("2024-01-01 10:00"), ts("2024-01-01 11:00"), ts("2024-01-01 12:00"), ts("2024-01-01 10:30"), ts("2024-01-01 11:30")],
            "avg_speed": [10.0, 11.0, 12.0, 20.0, 21.0],
        }
    )
    events = pd.DataFrame(
        {
            "trip_id": [3, 1, 2, 4, 5],
            "zone": [1, 1, 2, 3, 1],
            "event_ts": [ts("2024-01-01 12:30"), ts("2024-01-01 11:00"), ts("2024-01-01 10:29"), ts("2024-01-01 11:00"), ts("2024-01-01 09:59")],
        }
    )
    return events, features


def test_takes_latest_feature_not_after_event(join, small):
    events, features = small
    out = join(events, features, key="zone")
    by_trip = out.set_index("trip_id")["avg_speed"]
    assert by_trip[3] == 12.0
    assert by_trip[1] == 11.0
    assert pd.isna(by_trip[2])
    assert pd.isna(by_trip[4])
    assert pd.isna(by_trip[5])


def test_preserves_event_order_and_columns(join, small):
    events, features = small
    out = join(events, features, key="zone")
    assert out["trip_id"].tolist() == [3, 1, 2, 4, 5]
    assert list(out.columns) == ["trip_id", "zone", "event_ts", "avg_speed", "feature_timestamp"]
    assert list(out.index) == list(range(5))
    assert len(out) == len(events)


def test_inputs_are_not_mutated(join, small):
    events, features = small
    before = (events.copy(), features.copy())
    join(events, features, key="zone")
    pd.testing.assert_frame_equal(events, before[0])
    pd.testing.assert_frame_equal(features, before[1])


def test_works_with_unsorted_features_and_custom_names(join):
    features = pd.DataFrame({"z": [1, 1], "available_at": [ts("2024-01-01 12:00"), ts("2024-01-01 10:00")], "v": [2.0, 1.0]})
    events = pd.DataFrame({"z": [1], "t": [ts("2024-01-01 11:00")]})
    out = join(events, features, key="z", event_ts="t", feature_ts="available_at")
    assert out.loc[0, "v"] == 1.0
    assert out.loc[0, "feature_timestamp"] == ts("2024-01-01 10:00")


def test_tolerance_drops_stale_features(join, small):
    events, features = small
    out = join(events, features, key="zone", tolerance=pd.Timedelta("30min"))
    by_trip = out.set_index("trip_id")["avg_speed"]
    assert by_trip[3] == 12.0
    assert by_trip[1] == 11.0


def test_tolerance_zero_window_keeps_only_exact_matches(join, small):
    events, features = small
    out = join(events, features, key="zone", tolerance=pd.Timedelta(0))
    assert out.set_index("trip_id")["avg_speed"][1] == 11.0
    assert pd.isna(out.set_index("trip_id")["avg_speed"][3])


def hourly_features(df):
    hour = df["pickup"].dt.floor("h")
    table = df.assign(hour=hour).groupby(["zone", "hour"]).agg(avg_speed=("speed", "mean"), trips=("speed", "size")).reset_index()
    table["feature_ts"] = table["hour"] + pd.Timedelta(hours=1)
    return table.drop(columns="hour")


@pytest.fixture(scope="module")
def real_trips():
    path = mlopskit.real_month("nyc-tlc", "2019-03")
    df = pd.read_parquet(path, columns=["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "trip_distance"])
    df = df.sample(60_000, random_state=0)
    hours = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 3600
    df = df[(hours > 1 / 60) & (df["trip_distance"] > 0.1)].assign(speed=lambda d: d["trip_distance"] / hours[d.index])
    df = df[df["speed"] < 80].rename(columns={"tpep_pickup_datetime": "pickup", "PULocationID": "zone"})
    return df[["pickup", "zone", "speed"]].reset_index(drop=True)


def test_real_data_never_uses_future_features(join, real_trips):
    features = hourly_features(real_trips.iloc[:40_000])
    events = real_trips.iloc[40_000:].rename(columns={"pickup": "event_ts"})[["event_ts", "zone"]].reset_index(drop=True)
    out = join(events, features, key="zone")
    matched = out.dropna(subset=["feature_timestamp"])
    assert len(matched) > 0.5 * len(out)
    assert (matched["feature_timestamp"] <= matched["event_ts"]).all()


def test_real_data_matches_brute_force(join, real_trips):
    features = hourly_features(real_trips.iloc[:40_000])
    events = real_trips.iloc[40_000:40_300].rename(columns={"pickup": "event_ts"})[["event_ts", "zone"]].reset_index(drop=True)
    out = join(events, features, key="zone")
    for row in out.itertuples():
        pool = features[(features["zone"] == row.zone) & (features["feature_ts"] <= row.event_ts)]
        if pool.empty:
            assert pd.isna(row.avg_speed)
        else:
            best = pool.loc[pool["feature_ts"].idxmax()]
            assert row.avg_speed == pytest.approx(best["avg_speed"])
            assert row.trips == best["trips"]
            assert row.feature_timestamp == best["feature_ts"]
