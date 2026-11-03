import importlib.util
from pathlib import Path

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
N = 20_000
CLIENT_TIMEOUT_MS = 1000.0


def traffic(seed=11, slow_share=0.0, shed_share=0.0):
    rng = np.random.default_rng(seed)
    traces, seen = [], []
    for i in range(N):
        roll = rng.random()
        fetch = float(rng.lognormal(np.log(30), 0.3))
        if roll < slow_share:
            fetch = float(rng.lognormal(np.log(900), 0.5))
        infer = float(rng.lognormal(np.log(25), 0.2))
        failed = rng.random() < 0.0005
        handler = fetch + infer + 3.0
        outer = handler + 5.0
        status = 500 if failed else 200
        if shed_share and slow_share <= roll < slow_share + shed_share:
            traces.append({"id": f"r{i}", "spans": [{"name": "gateway", "parent": None, "status": 503, "duration_ms": 2.0}]})
            seen.append((503, 2.0))
            continue
        edge_status, edge_ms = (504, CLIENT_TIMEOUT_MS) if outer > CLIENT_TIMEOUT_MS else (status, outer)
        traces.append({"id": f"r{i}", "spans": [
            {"name": "gateway", "parent": None, "status": edge_status, "duration_ms": edge_ms},
            {"name": "handler", "parent": "gateway", "status": status, "duration_ms": handler},
            {"name": "features", "parent": "handler", "status": 200, "duration_ms": fetch},
            {"name": "predict", "parent": "handler", "status": status, "duration_ms": infer},
        ]})
        seen.append((edge_status, edge_ms))
    rng.shuffle(order := np.arange(N))
    return [traces[k] for k in order], [seen[k] for k in order]


def experienced(seen):
    ok = [ms for status, ms in seen if status < 500]
    return len(ok) / len(seen), sum(1 for ms in ok if ms <= 300) / len(ok), len(ok)


def load(path):
    spec = importlib.util.spec_from_file_location(f"slis_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bad_day():
    return traffic(slow_share=0.08, shed_share=0.01)


@pytest.fixture(scope="module")
def good_day():
    return traffic(seed=12)


def test_regression_original_dashboard_is_green_while_users_suffer(bad_day):
    traces, seen = bad_day
    original = load(FIXTURES / "slis.original.py")
    report = original.slo_report(traces)
    assert report["availability"]["met"] and report["latency_ok"]["met"]
    users_avail, users_fast, _ = experienced(seen)
    assert users_avail < 0.97
    assert users_fast < 0.97


def test_availability_matches_what_users_experienced(bad_day):
    traces, seen = bad_day
    value, events = ex.module("slis.py").availability(traces)
    expected, _, _ = experienced(seen)
    assert events == N
    assert value == pytest.approx(expected)


def test_latency_matches_what_users_experienced(bad_day):
    traces, seen = bad_day
    value, events = ex.module("slis.py").latency_ok(traces)
    _, expected, served = experienced(seen)
    assert events == served
    assert value == pytest.approx(expected)


def test_report_shows_the_breach(bad_day):
    report = ex.module("slis.py").slo_report(bad_day[0])
    assert report["availability"]["met"] is False
    assert report["latency_ok"]["met"] is False
    assert report["availability"]["target"] == 0.995


def test_healthy_day_stays_green(good_day):
    traces, seen = good_day
    report = ex.module("slis.py").slo_report(traces)
    expected_avail, expected_fast, _ = experienced(seen)
    assert report["availability"]["met"] is True and report["latency_ok"]["met"] is True
    assert report["availability"]["value"] == pytest.approx(expected_avail)
    assert report["latency_ok"]["value"] == pytest.approx(expected_fast)


def test_no_traffic_is_not_green():
    report = ex.module("slis.py").slo_report([])
    assert report["availability"]["value"] is None and report["availability"]["met"] is False
    assert report["latency_ok"]["events"] == 0
