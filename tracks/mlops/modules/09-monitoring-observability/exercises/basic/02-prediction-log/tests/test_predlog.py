import io
import json
import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
T0 = datetime(2019, 3, 4, 8, 15, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def mod():
    return ex.module("predlog.py")


def write(mod, **overrides):
    stream = io.StringIO()
    args = dict(request_id="r1", model_version="3", features={"trip_distance_km": 4.2, "hour": 8}, prediction=612.5,
                fallback=False, ts=T0)
    args.update(overrides)
    mod.log_prediction(stream, **args)
    return stream.getvalue()


def line(rid, prediction, ts=T0, version="3"):
    return json.dumps({"ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "request_id": rid, "model_version": version,
                       "prediction": prediction, "fallback": False, "features": {}})


def test_one_json_line_with_agreed_keys(mod):
    text = write(mod)
    assert text.endswith("\n") and text.count("\n") == 1
    record = json.loads(text)
    assert set(record) == {"ts", "request_id", "model_version", "prediction", "fallback", "features"}
    assert record["ts"] == "2019-03-04T08:15:00Z"
    assert record["request_id"] == "r1" and record["prediction"] == 612.5 and record["fallback"] is False


def test_timestamp_is_converted_to_utc(mod):
    local = datetime(2019, 3, 4, 15, 15, 0, tzinfo=timezone(timedelta(hours=7)))
    assert json.loads(write(mod, ts=local))["ts"] == "2019-03-04T08:15:00Z"


def test_naive_timestamp_is_rejected(mod):
    with pytest.raises(ValueError):
        write(mod, ts=datetime(2019, 3, 4, 8, 15, 0))


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_prediction_is_rejected(mod, bad):
    with pytest.raises(ValueError):
        write(mod, prediction=bad)


def test_only_allowed_features_are_logged(mod):
    features = {"trip_distance_km": 3.0, "pickup_zone": "JFK", "rider_phone": "+84 90 000 0000", "rider_name": "A"}
    record = json.loads(write(mod, features=features))
    assert record["features"] == {"trip_distance_km": 3.0, "pickup_zone": "JFK"}
    assert "rider" not in write(mod, features=features)


def test_newlines_in_values_do_not_break_the_line(mod):
    text = write(mod, features={"pickup_zone": "Zone\nX"}, request_id="a\nb")
    assert text.count("\n") == 1
    assert json.loads(text)["features"]["pickup_zone"] == "Zone\nX"


def test_join_computes_error_and_reports_gaps(mod):
    lines = [line("a", 600.0), line("b", 900.0), line("c", 300.0)]
    labels = [{"request_id": "a", "actual_seconds": 650}, {"request_id": "b", "actual_seconds": 840},
              {"request_id": "zzz", "actual_seconds": 100}]
    result = mod.join_labels(lines, labels)
    assert [(r["request_id"], r["abs_error"]) for r in result.rows] == [("a", 50.0), ("b", 60.0)]
    assert set(result.rows[0]) >= {"request_id", "ts", "model_version", "prediction", "actual_seconds", "abs_error"}
    assert result.unmatched_predictions == 1
    assert result.orphan_labels == 1
    assert result.bad_lines == 0 and result.bad_labels == 0


def test_join_survives_corrupt_input(mod):
    lines = ["", "not json", json.dumps([1, 2]), json.dumps({"request_id": "x"}),
             json.dumps({"ts": "2019-03-04T08:15:00Z", "request_id": "n", "prediction": None}),
             line("a", 600.0)]
    labels = [{"request_id": "a", "actual_seconds": 700}, {"request_id": "b", "actual_seconds": None},
              {"request_id": "c", "actual_seconds": math.nan}, {"actual_seconds": 5}]
    result = mod.join_labels(lines, labels)
    assert [r["request_id"] for r in result.rows] == ["a"]
    assert result.bad_lines == 4
    assert result.bad_labels == 3
    assert result.orphan_labels == 0


def test_duplicate_request_id_keeps_latest_prediction(mod):
    lines = [line("a", 500.0, T0 + timedelta(seconds=5), "4"), line("a", 400.0, T0, "3")]
    result = mod.join_labels(lines, [{"request_id": "a", "actual_seconds": 450}])
    assert len(result.rows) == 1
    assert result.rows[0]["prediction"] == 500.0 and result.rows[0]["model_version"] == "4"
    assert result.unmatched_predictions == 0


def test_rows_are_sorted_by_time_then_id(mod):
    lines = [line("b", 1.0, T0 + timedelta(minutes=1)), line("z", 1.0, T0), line("a", 1.0, T0)]
    labels = [{"request_id": r, "actual_seconds": 2.0} for r in "abz"]
    assert [r["request_id"] for r in mod.join_labels(lines, labels).rows] == ["a", "z", "b"]


def test_join_accepts_iterators(mod):
    result = mod.join_labels(iter([line("a", 1.0)]), iter([{"request_id": "a", "actual_seconds": 3}]))
    assert len(result.rows) == 1


def test_real_trips_round_trip():
    import pyarrow.parquet as pq

    path = mlopskit.real_month("nyc-tlc", "2019-03")
    columns = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance", "PULocationID", "DOLocationID"]
    batch = next(pq.ParquetFile(path).iter_batches(batch_size=40000, columns=columns))
    trips = batch.to_pandas().sample(2000, random_state=0).reset_index(drop=True)
    trips["actual"] = (trips["tpep_dropoff_datetime"] - trips["tpep_pickup_datetime"]).dt.total_seconds()
    trips = trips[(trips["actual"] >= 60) & (trips["actual"] <= 7200) & (trips["trip_distance"] > 0)].reset_index(drop=True)
    trips["km"] = trips["trip_distance"] * 1.609
    trips["pred"] = 240.0 + 150.0 * trips["km"]
    mod = Exercise(__file__).module("predlog.py")
    stream = io.StringIO()
    for i, row in trips.iterrows():
        mod.log_prediction(stream, request_id=f"trip-{i}", model_version="3", prediction=float(row["pred"]), fallback=False,
                           ts=row["tpep_pickup_datetime"].to_pydatetime().replace(tzinfo=timezone.utc),
                           features={"trip_distance_km": float(row["km"]), "pickup_zone": int(row["PULocationID"]),
                                     "rider_phone": "secret"})
    text = stream.getvalue()
    assert "secret" not in text
    known = trips.iloc[: int(len(trips) * 0.8)]
    labels = [{"request_id": f"trip-{i}", "actual_seconds": float(a)} for i, a in zip(known.index, known["actual"])]
    result = mod.join_labels(text.splitlines(), labels)
    assert len(result.rows) == len(known)
    assert result.unmatched_predictions == len(trips) - len(known)
    expected = float(np.mean(np.abs(known["pred"].to_numpy() - known["actual"].to_numpy())))
    assert float(np.mean([r["abs_error"] for r in result.rows])) == pytest.approx(expected, rel=1e-9)
