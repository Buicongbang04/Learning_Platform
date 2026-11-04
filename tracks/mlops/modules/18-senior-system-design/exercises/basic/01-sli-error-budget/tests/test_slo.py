import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)
DAY = 86_400
STEP = 10
INCIDENT_START = DAY - 3_600


def generate(seed=7):
    rng = np.random.default_rng(seed)
    ts = np.arange(0, DAY, STEP)
    n = len(ts)
    error_p = np.where(ts >= INCIDENT_START, 0.10, 0.002)
    status = np.where(rng.random(n) < error_p, 503, 200)
    latency = rng.lognormal(np.log(120), 0.5, n)
    labelled = rng.random(n) < 0.3
    abs_error = np.abs(rng.normal(0, 4, n))
    age = rng.exponential(200, n)
    events = [
        {"ts": int(t), "status": int(s), "latency_ms": float(l), "abs_error_min": float(a) if lab else None, "feature_age_s": float(g)}
        for t, s, l, a, lab, g in zip(ts, status, latency, abs_error, labelled, age)
    ]
    arrays = {"ts": ts, "status": status, "latency": latency, "labelled": labelled, "abs_error": abs_error, "age": age}
    return events, arrays


@pytest.fixture(scope="module")
def slo():
    return ex.module("slo.py")


@pytest.fixture(scope="module")
def data():
    return generate()


def test_availability_on_generated_log(slo, data):
    events, a = data
    assert slo.availability(events) == pytest.approx(np.mean(a["status"] < 500))
    assert slo.availability([]) is None


def test_latency_counts_only_served_requests(slo, data):
    events, a = data
    served = a["status"] < 500
    expected = np.mean(a["latency"][served] <= 300)
    assert slo.latency_sli(events, 300) == pytest.approx(expected)
    assert slo.latency_sli([{"ts": 0, "status": 503, "latency_ms": 5.0, "abs_error_min": None, "feature_age_s": 1.0}], 300) is None


def test_quality_uses_only_labelled_predictions(slo, data):
    events, a = data
    expected = np.mean(a["abs_error"][a["labelled"]] <= 5)
    assert slo.quality_sli(events, 5) == pytest.approx(expected)
    unlabelled = [dict(e, abs_error_min=None) for e in events[:50]]
    assert slo.quality_sli(unlabelled, 5) is None


def test_freshness_on_generated_log(slo, data):
    events, a = data
    assert slo.freshness_sli(events, 600) == pytest.approx(np.mean(a["age"] <= 600))
    assert slo.freshness_sli([], 600) is None


def test_thresholds_are_inclusive(slo):
    events = [{"ts": 0, "status": 200, "latency_ms": 300.0, "abs_error_min": 5.0, "feature_age_s": 600.0}]
    assert slo.latency_sli(events, 300) == 1.0
    assert slo.quality_sli(events, 5) == 1.0
    assert slo.freshness_sli(events, 600) == 1.0


def test_budget_minutes(slo):
    assert slo.budget_minutes(0.995, 30) == pytest.approx(216)
    assert slo.budget_minutes(0.999, 30) == pytest.approx(43.2)
    assert slo.budget_minutes(0.99, 7) == pytest.approx(100.8)


def test_error_budget_report(slo):
    report = slo.error_budget(0.997, 0.995, 1_000_000)
    assert report["allowed_bad"] == pytest.approx(5_000)
    assert report["bad"] == pytest.approx(3_000)
    assert report["remaining"] == pytest.approx(0.4)
    overspent = slo.error_budget(0.99, 0.995, 1_000_000)
    assert overspent["remaining"] == pytest.approx(-1.0)


def test_burn_rate(slo):
    assert slo.burn_rate(0.072, 0.995) == pytest.approx(14.4)
    assert slo.burn_rate(0.005, 0.995) == pytest.approx(1.0)
    assert slo.burn_rate(0.0, 0.98) == 0.0


def test_window_burn_rates_see_the_incident(slo, data):
    events, a = data
    rates = slo.window_burn_rates(events, 0.995, DAY, [300, 3_600, 21_600])
    assert set(rates) == {300, 3_600, 21_600}
    for window in rates:
        inside = (a["ts"] >= DAY - window) & (a["ts"] < DAY)
        expected = np.mean(a["status"][inside] >= 500) / 0.005
        assert rates[window] == pytest.approx(expected)
    assert rates[3_600] > 14.4
    assert rates[21_600] < rates[3_600]


def test_window_bounds_are_half_open(slo):
    events = [
        {"ts": 100, "status": 500, "latency_ms": 1.0, "abs_error_min": None, "feature_age_s": 1.0},
        {"ts": 199, "status": 200, "latency_ms": 1.0, "abs_error_min": None, "feature_age_s": 1.0},
        {"ts": 200, "status": 500, "latency_ms": 1.0, "abs_error_min": None, "feature_age_s": 1.0},
    ]
    rates = slo.window_burn_rates(events, 0.99, 200, [100, 50])
    assert rates[100] == pytest.approx(50.0)
    assert rates[50] == pytest.approx(0.0)
    assert slo.window_burn_rates([], 0.99, 200, [60]) == {60: 0.0}
