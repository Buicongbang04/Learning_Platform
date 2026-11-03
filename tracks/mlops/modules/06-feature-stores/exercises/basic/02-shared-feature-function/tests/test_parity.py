import math

import numpy as np
import pandas as pd
import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
COLUMNS = ["hour_sin", "hour_cos", "is_night", "is_weekend", "zone_id", "zone_known", "trip_distance"]


@pytest.fixture
def mod():
    return ex.module("features.py")


def frame(rows):
    return pd.DataFrame(rows, columns=["pickup_ts", "zone_id", "trip_distance"])


def test_feature_columns_and_dtypes(mod):
    out = mod.compute_features(frame([["2024-03-05 14:30:00", 132, 3.2]]))
    assert list(out.columns) == COLUMNS
    assert all(dtype == "float64" for dtype in out.dtypes)
    assert mod.FEATURE_COLUMNS == COLUMNS


def test_hour_wraps_around_midnight(mod):
    out = mod.compute_features(frame([[f"2024-03-05 {h:02d}:10:00", 10, 1.0] for h in (22, 23, 0, 1, 12)]))
    pts = out[["hour_sin", "hour_cos"]].to_numpy()
    gap_23_0 = np.linalg.norm(pts[1] - pts[2])
    gap_0_1 = np.linalg.norm(pts[2] - pts[3])
    gap_22_23 = np.linalg.norm(pts[0] - pts[1])
    assert gap_23_0 == pytest.approx(gap_0_1)
    assert gap_23_0 == pytest.approx(gap_22_23)
    assert gap_23_0 < np.linalg.norm(pts[2] - pts[4])
    assert out.loc[2, "hour_sin"] == pytest.approx(0.0)
    assert out.loc[2, "hour_cos"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "stamp,night",
    [("2024-03-05 21:59:00", 0), ("2024-03-05 22:00:00", 1), ("2024-03-05 23:59:00", 1), ("2024-03-06 00:00:00", 1),
     ("2024-03-06 05:59:00", 1), ("2024-03-06 06:00:00", 0)],
)
def test_night_boundaries(mod, stamp, night):
    assert mod.compute_features(frame([[stamp, 10, 1.0]])).loc[0, "is_night"] == night


@pytest.mark.parametrize("stamp,weekend", [("2024-03-08 23:59:00", 0), ("2024-03-09 00:00:00", 1), ("2024-03-10 23:59:00", 1), ("2024-03-11 00:00:00", 0)])
def test_weekend_boundaries(mod, stamp, weekend):
    assert mod.compute_features(frame([[stamp, 10, 1.0]])).loc[0, "is_weekend"] == weekend


def test_missing_or_invalid_zone_uses_default(mod):
    out = mod.compute_features(frame([["2024-03-05 10:00:00", None, 1.0], ["2024-03-05 10:00:00", np.nan, 1.0],
                                      ["2024-03-05 10:00:00", 0, 1.0], ["2024-03-05 10:00:00", 999, 1.0],
                                      ["2024-03-05 10:00:00", 265, 1.0], ["2024-03-05 10:00:00", 1, 1.0]]))
    assert out["zone_id"].tolist() == [0, 0, 0, 0, 265, 1]
    assert out["zone_known"].tolist() == [0, 0, 0, 0, 1, 1]


def test_missing_and_negative_distance(mod):
    out = mod.compute_features(frame([["2024-03-05 10:00:00", 5, None], ["2024-03-05 10:00:00", 5, -2.0], ["2024-03-05 10:00:00", 5, 0.0]]))
    assert out["trip_distance"].tolist() == [mod.DEFAULT_DISTANCE, 0.0, 0.0]
    assert mod.DEFAULT_DISTANCE == 1.5


def test_keeps_index(mod):
    df = frame([["2024-03-05 10:00:00", 5, 1.0], ["2024-03-05 11:00:00", 6, 2.0]])
    df.index = [40, 7]
    assert mod.compute_features(df).index.tolist() == [40, 7]


def test_empty_frame_has_columns(mod):
    out = mod.compute_features(frame([]).astype({"pickup_ts": "datetime64[ns]"}))
    assert list(out.columns) == COLUMNS and len(out) == 0


def test_serve_one_defaults_and_errors(mod):
    out = mod.serve_one({"pickup_ts": "2024-03-05T23:15:00"})
    assert out["zone_id"] == 0 and out["zone_known"] == 0 and out["trip_distance"] == 1.5
    assert out["is_night"] == 1
    with pytest.raises(ValueError):
        mod.serve_one({"zone_id": 5})


def test_train_and_serve_both_go_through_compute_features(mod, monkeypatch):
    calls = []
    real = mod.compute_features

    def spy(df):
        calls.append(len(df))
        out = real(df)
        out["trip_distance"] = out["trip_distance"] + 1000.0
        return out

    monkeypatch.setattr(mod, "compute_features", spy)
    df = frame([["2024-03-05 10:00:00", 5, 1.0], ["2024-03-05 11:00:00", 6, 2.0]])
    assert mod.train_matrix(df)["trip_distance"].tolist() == [1001.0, 1002.0]
    assert mod.serve_one({"pickup_ts": "2024-03-05 10:00:00", "zone_id": 5, "trip_distance": 1.0})["trip_distance"] == 1001.0
    assert calls == [2, 1]


def test_real_data_batch_equals_online(mod):
    path = mlopskit.real_month("nyc-tlc", "2019-03")
    df = pd.read_parquet(path, columns=["tpep_pickup_datetime", "PULocationID", "trip_distance"]).sample(400, random_state=0)
    df = df.rename(columns={"tpep_pickup_datetime": "pickup_ts", "PULocationID": "zone_id"}).reset_index(drop=True)
    df.loc[::25, "zone_id"] = np.nan
    df.loc[::40, "trip_distance"] = np.nan
    batch = mod.train_matrix(df)
    stamps, zones, dists = df["pickup_ts"].tolist(), df["zone_id"].tolist(), df["trip_distance"].tolist()
    for i in range(len(df)):
        request = {"pickup_ts": stamps[i].isoformat(), "zone_id": None if math.isnan(zones[i]) else int(zones[i]),
                   "trip_distance": None if math.isnan(dists[i]) else float(dists[i])}
        online = mod.serve_one(request)
        for col in COLUMNS:
            assert online[col] == pytest.approx(batch.loc[i, col]), (i, col, request)
