import importlib
import json
import re
import sys
import tomllib
from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
PICKUP = "tpep_pickup_datetime"
DROPOFF = "tpep_dropoff_datetime"
DIRTY = 10


def make_trips(n: int = 3000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    distance = np.round(rng.gamma(2.0, 1.5, n) + 0.3, 2)
    pickup = pd.Timestamp("2019-01-07") + pd.to_timedelta(rng.integers(0, 14 * 24 * 60, n), unit="m")
    rush = pickup.hour.isin([16, 17, 18, 19])
    minutes = 4 + 3.2 * distance + 3.0 * rush + rng.normal(0, 1.5, n)
    minutes = np.clip(minutes, 1, 120)
    frame = pd.DataFrame(
        {
            PICKUP: pickup,
            DROPOFF: pickup + pd.to_timedelta(minutes, unit="m"),
            "trip_distance": distance,
            "PULocationID": rng.integers(1, 266, n),
            "DOLocationID": rng.integers(1, 266, n),
        }
    )
    frame.loc[:DIRTY - 1, DROPOFF] = frame.loc[:DIRTY - 1, PICKUP] - pd.Timedelta(minutes=5)
    frame.loc[DIRTY:2 * DIRTY - 1, "trip_distance"] = 0.0
    frame.loc[2 * DIRTY:3 * DIRTY - 1, DROPOFF] = frame.loc[2 * DIRTY:3 * DIRTY - 1, PICKUP] + pd.Timedelta(hours=7)
    return frame


@pytest.fixture
def eta(monkeypatch):
    def purge():
        for name in [m for m in sys.modules if m == "eta_mini" or m.startswith("eta_mini.")]:
            del sys.modules[name]

    purge()
    monkeypatch.syspath_prepend(str(ex.path("src")))
    yield SimpleNamespace(
        data=importlib.import_module("eta_mini.data"),
        features=importlib.import_module("eta_mini.features"),
        model=importlib.import_module("eta_mini.model"),
        cli=importlib.import_module("eta_mini.cli"),
    )
    purge()


@pytest.fixture
def trips_csv(tmp_path):
    path = tmp_path / "trips.csv"
    make_trips().to_csv(path, index=False)
    return path


def test_pyproject_is_a_real_package_definition():
    config = tomllib.loads(ex.read("pyproject.toml"))
    project = config["project"]
    assert project["name"] == "eta-mini"
    assert project.get("requires-python", "").startswith(">=3."), "Thiếu requires-python"
    dependencies = " ".join(project.get("dependencies", [])).lower()
    for name in ("pandas", "scikit-learn", "pyarrow", "joblib"):
        assert name in dependencies, f"Thiếu dependency {name}"
    assert project["scripts"]["eta-train"] == "eta_mini.cli:main"
    assert "setuptools" in " ".join(config["build-system"]["requires"])
    assert config["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]


def test_no_hardcoded_machine_paths_in_package():
    offenders = []
    for path in ex.path("src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"(/home/|/Users/|[A-Za-z]:\\\\|Downloads|Desktop)", text):
            offenders.append(path.name)
    assert not offenders, f"Đường dẫn của máy cá nhân còn trong: {offenders}"


def test_load_trips_reads_only_trip_columns_and_samples_deterministically(eta, trips_csv):
    full = eta.data.load_trips(trips_csv)
    assert list(full.columns) == eta.data.TRIP_COLUMNS
    assert len(full) == 3000
    assert pd.api.types.is_datetime64_any_dtype(full[PICKUP])
    first = eta.data.load_trips(trips_csv, max_rows=500, seed=1)
    again = eta.data.load_trips(trips_csv, max_rows=500, seed=1)
    other = eta.data.load_trips(trips_csv, max_rows=500, seed=2)
    assert len(first) == 500
    pd.testing.assert_frame_equal(first, again)
    assert not first.equals(other)


def test_load_trips_reads_parquet(eta, tmp_path):
    path = tmp_path / "trips.parquet"
    frame = make_trips(400)
    frame["extra_column"] = 1
    frame.to_parquet(path)
    loaded = eta.data.load_trips(path)
    assert list(loaded.columns) == eta.data.TRIP_COLUMNS
    assert len(loaded) == 400


def test_clean_applies_the_notebook_rules(eta):
    cleaned = eta.data.clean(make_trips())
    assert len(cleaned) == 3000 - 3 * DIRTY
    assert cleaned["duration_min"].between(0, 180, inclusive="right").all()
    assert (cleaned["trip_distance"] > 0).all()


def test_build_features_shape_and_order(eta):
    cleaned = eta.data.clean(make_trips(200))
    features = eta.features.build_features(cleaned)
    assert list(features.columns) == eta.features.FEATURES
    assert len(features) == len(cleaned)
    assert features["hour"].between(0, 23).all()
    assert features["dow"].between(0, 6).all()


def test_train_is_callable_and_beats_the_mean_baseline(eta):
    cleaned = eta.data.clean(make_trips())
    result = eta.model.train(cleaned, seed=0)
    assert result.n_train + result.n_test == len(cleaned)
    assert result.n_test == pytest.approx(0.2 * len(cleaned), abs=1)
    baseline = float((cleaned["duration_min"] - cleaned["duration_min"].mean()).abs().mean())
    assert result.mae < 0.5 * baseline
    predictions = eta.model.predict(result.model, cleaned.head(5))
    assert len(predictions) == 5
    assert np.isfinite(predictions).all()


def test_train_same_seed_same_mae(eta):
    cleaned = eta.data.clean(make_trips())
    assert eta.model.train(cleaned, seed=3).mae == eta.model.train(cleaned, seed=3).mae


def run_cli(tmp_path, *args, timeout=180):
    return run_sandboxed(
        [sys.executable, "-m", "eta_mini", *args],
        writable=[tmp_path],
        cwd=tmp_path,
        env={"PYTHONPATH": str(ex.path("src")), "OMP_NUM_THREADS": "2"},
        timeout=timeout,
    )


def test_cli_trains_and_writes_model(tmp_path, trips_csv):
    out = tmp_path / "out" / "model.joblib"
    out.parent.mkdir()
    result = run_cli(tmp_path, "--data", str(trips_csv), "--out", str(out), "--seed", "0", "--max-rows", "2000")
    assert result.returncode == 0, result.stderr[-1500:]
    summary = json.loads(result.stdout.strip().splitlines()[-1])
    assert set(summary) == {"mae", "n_train", "n_test"}
    assert 0 < summary["mae"] < 5
    assert hasattr(joblib.load(out), "predict")


def test_real_january_sample_trains(eta):
    path = ex.dataset("nyc-tlc") / "yellow_tripdata_2019-01.parquet"
    trips = eta.data.clean(eta.data.load_trips(path, max_rows=30000, seed=0))
    result = eta.model.train(trips, seed=0)
    baseline = float((trips["duration_min"] - trips["duration_min"].median()).abs().mean())
    assert result.mae < 0.8 * baseline
