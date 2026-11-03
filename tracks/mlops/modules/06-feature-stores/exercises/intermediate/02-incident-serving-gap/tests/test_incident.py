import importlib.util
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingRegressor

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
KM = 1.609344


def load(path):
    spec = importlib.util.spec_from_file_location(f"incident_{uuid.uuid4().hex[:8]}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def world():
    path = mlopskit.real_month("nyc-tlc", "2019-03")
    df = pd.read_parquet(path, columns=["tpep_pickup_datetime", "PULocationID", "trip_distance", "fare_amount"])
    df = df[(df["trip_distance"] > 0.1) & (df["trip_distance"] < 30) & (df["fare_amount"] > 2) & (df["fare_amount"] < 150)]
    df = df.sample(24_000, random_state=0).rename(columns={"tpep_pickup_datetime": "pickup_ts", "PULocationID": "zone_id"})
    train, test = df.iloc[:20_000].reset_index(drop=True), df.iloc[20_000:].reset_index(drop=True)
    return {"train": train, "test": test}


def fit(module, world):
    train = world["train"]
    return GradientBoostingRegressor(n_estimators=60, max_depth=4, random_state=0).fit(module.build_features(train), train["fare_amount"])


def requests_for(test):
    stamps, zones, miles = test["pickup_ts"].tolist(), test["zone_id"].tolist(), test["trip_distance"].tolist()
    return [{"pickup_ts": stamps[i].isoformat(), "zone_id": int(zones[i]), "distance_km": miles[i] * KM} for i in range(len(test))]


def replay(module, world):
    model = fit(module, world)
    test = world["test"]
    offline = model.predict(module.build_features(test))
    service = module.FareService(model)
    online = np.array([service.predict(r) for r in requests_for(test)])
    return test, offline, online


@pytest.fixture(scope="module")
def replayed(world):
    return replay(ex.module("service.py"), world)


def test_online_predictions_match_offline_for_same_trips(replayed):
    _, offline, online = replayed
    assert np.max(np.abs(online - offline)) < 1e-6


def test_online_mae_equals_offline_mae(replayed):
    test, offline, online = replayed
    mae_off = np.mean(np.abs(offline - test["fare_amount"]))
    mae_on = np.mean(np.abs(online - test["fare_amount"]))
    assert mae_on == pytest.approx(mae_off, rel=1e-3)


def test_long_trips_are_not_biased(replayed):
    test, offline, online = replayed
    long = (test["trip_distance"] > 10).to_numpy()
    assert long.sum() > 20
    assert abs(np.mean(online[long] - offline[long])) < 0.01


def test_request_contract_defaults_and_errors(world):
    module = ex.module("service.py")
    service = module.FareService(fit(module, world))
    base = {"pickup_ts": "2019-03-12T08:30:00", "distance_km": 8.0}
    assert isinstance(service.predict(base), float)
    assert service.predict(base) == pytest.approx(service.predict({**base, "zone_id": 0}))
    assert service.predict({**base, "zone_id": None}) == pytest.approx(service.predict(base))
    with pytest.raises(ValueError):
        service.predict({"pickup_ts": "2019-03-12T08:30:00"})


def test_build_features_output_is_unchanged():
    module = ex.module("service.py")
    df = pd.DataFrame({"pickup_ts": ["2019-03-09 23:30:00", "2019-03-11 06:00:00"], "zone_id": [132.0, None], "trip_distance": [10.0, 2.5]})
    out = module.build_features(df)
    assert list(out.columns) == ["trip_distance", "hour", "is_weekend", "zone_id"]
    assert out.to_numpy().tolist() == [[10.0, 23.0, 1.0, 132.0], [2.5, 6.0, 0.0, 0.0]]


def test_symptom_is_reproduced_by_the_original_service(world):
    test, offline, online = replay(load(FIXTURES / "service_v1.py"), world)
    mae_off = np.mean(np.abs(offline - test["fare_amount"]))
    mae_on = np.mean(np.abs(online - test["fare_amount"]))
    long = (test["trip_distance"] > 10).to_numpy()
    assert mae_on > 2 * mae_off
    assert np.mean(online[long] - offline[long]) > 5
