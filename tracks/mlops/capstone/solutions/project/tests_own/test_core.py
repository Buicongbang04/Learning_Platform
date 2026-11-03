import numpy as np
import pandas as pd
import pytest

from eta.clock import add_months, months_between
from eta.drift import psi
from eta.features import FEATURES, clean, make_features
from eta.labels import published
from eta.quality import join_labels, monthly_quality


def trips() -> pd.DataFrame:
    pickup = pd.to_datetime(["2019-01-05 08:00", "2019-01-06 09:00", "2019-02-01 10:00", "2019-01-07 11:00"])
    return pd.DataFrame({
        "tpep_pickup_datetime": pickup,
        "tpep_dropoff_datetime": pickup + pd.to_timedelta([600, 30, 600, 900], unit="s"),
        "PULocationID": [161, 161, 132, 300],
        "DOLocationID": [236, 236, 230, 236],
        "trip_distance": [2.0, 0.1, 9.0, 3.0],
    })


def test_clean_keeps_only_valid_trips_of_the_month():
    out = clean(trips(), "2019-01")
    assert len(out) == 1
    assert out["duration_s"].tolist() == [600.0]


def test_make_features_columns():
    assert list(make_features(clean(trips(), "2019-01")).columns) == FEATURES


def test_clock_and_label_delay():
    assert months_between("2019-12", "2020-02") == ["2019-12", "2020-01", "2020-02"]
    assert add_months("2020-01", -1) == "2019-12"
    assert not published("2020-03", "2020-03")
    assert published("2020-03", "2020-04")


def test_psi_zero_on_same_sample_and_positive_on_shift():
    x = pd.Series(np.random.default_rng(0).normal(size=2_000))
    assert psi(x, x) == pytest.approx(0.0, abs=1e-12)
    assert psi(x, x + 1.0) > 0.25


def test_quality_drops_unlabeled_requests():
    predictions = pd.DataFrame({"request_id": ["a", "b", "c"], "eta_s": [100.0, 200.0, 300.0],
                                "PULocationID": [132, 1, 1], "DOLocationID": [1, 1, 1]})
    labels = pd.DataFrame({"request_id": ["a", "b"], "duration_s": [110.0, 180.0]})
    quality = monthly_quality(join_labels(predictions, labels))
    assert quality["n"] == 2
    assert quality["mae"] == pytest.approx(15.0)
    assert quality["mae_airport"] == pytest.approx(10.0)
