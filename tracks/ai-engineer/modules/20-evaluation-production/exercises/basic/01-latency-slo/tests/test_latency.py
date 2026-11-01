import math

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def lat():
    return ex.module("latency.py")


# ---------- breakdown ----------

def test_breakdown_hand_example(lat):
    req = lat.Request(t_arrival=10.0, t_start=10.5, token_times=[11.0, 11.1, 11.3, 11.6])
    b = lat.breakdown(req)
    assert b["queue_s"] == pytest.approx(0.5)
    assert b["ttft_s"] == pytest.approx(1.0), "TTFT tính từ lúc request đến, gồm cả thời gian xếp hàng"
    assert b["service_ttft_s"] == pytest.approx(0.5)
    assert b["e2e_s"] == pytest.approx(1.6)
    assert b["tpot_s"] == pytest.approx(0.2), "(1.6 - 1.0) / 3 khoảng giữa các token"
    assert b["itl_s"] == pytest.approx([0.1, 0.2, 0.3])
    assert b["n_tokens"] == 4


def test_breakdown_single_token(lat):
    b = lat.breakdown(lat.Request(t_arrival=0.0, t_start=0.0, token_times=[0.25]))
    assert b["tpot_s"] == 0.0 and b["itl_s"] == [] and b["e2e_s"] == pytest.approx(0.25)


@pytest.mark.parametrize("req", [
    dict(t_arrival=0.0, t_start=0.1, token_times=[]),
    dict(t_arrival=1.0, t_start=0.5, token_times=[2.0]),
    dict(t_arrival=0.0, t_start=1.0, token_times=[0.5, 1.5]),
    dict(t_arrival=0.0, t_start=0.0, token_times=[1.0, 0.9]),
])
def test_breakdown_rejects_bad_timestamps(lat, req):
    with pytest.raises(ValueError):
        lat.breakdown(lat.Request(**req))


# ---------- bootstrap ----------

def test_bootstrap_matches_definition(lat):
    x = np.random.default_rng(1).lognormal(0.0, 0.6, size=150)
    point, lo, hi = lat.bootstrap_percentile_ci(x, 95, n_boot=1000, seed=7)
    rng = np.random.default_rng(7)
    idx = rng.integers(0, len(x), size=(1000, len(x)))
    stats = np.percentile(x[idx], 95, axis=1)
    exp_lo, exp_hi = np.percentile(stats, [2.5, 97.5])
    assert point == pytest.approx(np.percentile(x, 95))
    assert lo == pytest.approx(exp_lo) and hi == pytest.approx(exp_hi)
    assert all(isinstance(v, float) for v in (point, lo, hi))


def test_bootstrap_level_and_seed(lat):
    x = np.random.default_rng(2).exponential(1.0, size=200)
    _, lo95, hi95 = lat.bootstrap_percentile_ci(x, 99, seed=0)
    _, lo80, hi80 = lat.bootstrap_percentile_ci(x, 99, seed=0, level=0.8)
    assert lo95 <= lo80 <= hi80 <= hi95, "khoảng 80% nằm trong khoảng 95%"
    assert lat.bootstrap_percentile_ci(x, 99, seed=3) == lat.bootstrap_percentile_ci(x, 99, seed=3)


def test_bootstrap_coverage_on_known_distribution(lat):
    rng = np.random.default_rng(0)
    true_p95 = math.log(20)
    covered = 0
    reps = 300
    for _ in range(reps):
        x = rng.exponential(1.0, size=200)
        _, lo, hi = lat.bootstrap_percentile_ci(x, 95, n_boot=400, seed=int(rng.integers(1 << 30)))
        covered += lo <= true_p95 <= hi
    assert 0.85 <= covered / reps <= 0.99, f"khoảng 95% chứa p95 thật {covered}/{reps} lần"


def test_bootstrap_rejects_bad_input(lat):
    with pytest.raises(ValueError):
        lat.bootstrap_percentile_ci([1.0], 95)
    with pytest.raises(ValueError):
        lat.bootstrap_percentile_ci([1.0, 2.0], 120)


# ---------- histogram_quantile ----------

def test_histogram_quantile_interpolates_inside_bucket(lat):
    bounds = [0.1, 0.25, 0.5, 1.0, math.inf]
    cum = [10, 40, 80, 95, 100]
    assert lat.histogram_quantile(bounds, cum, 0.5) == pytest.approx(0.25 + 0.25 * (50 - 40) / 40)
    assert lat.histogram_quantile(bounds, cum, 0.05) == pytest.approx(0.05), "bucket đầu nội suy từ 0"
    assert lat.histogram_quantile(bounds, cum, 0.9) == pytest.approx(0.5 + 0.5 * (90 - 80) / 15)


def test_histogram_quantile_inf_bucket_and_empty(lat):
    bounds = [0.1, 0.25, 0.5, 1.0, math.inf]
    cum = [10, 40, 80, 95, 100]
    assert lat.histogram_quantile(bounds, cum, 0.99) == pytest.approx(1.0), "rơi vào bucket +Inf thì trả cận trên hữu hạn lớn nhất"
    assert math.isnan(lat.histogram_quantile(bounds, [0, 0, 0, 0, 0], 0.5))


def test_histogram_quantile_close_to_exact_on_uniform(lat):
    x = np.random.default_rng(0).uniform(0, 2, size=100_000)
    bounds = list(np.linspace(0.1, 2.0, 20))
    cum = [int((x <= b).sum()) for b in bounds]
    for q in (0.5, 0.9, 0.99):
        assert lat.histogram_quantile(bounds, cum, q) == pytest.approx(np.quantile(x, q), abs=0.01)


def test_histogram_quantile_rejects_bad_input(lat):
    with pytest.raises(ValueError):
        lat.histogram_quantile([0.5, 0.1], [1, 2], 0.5)
    with pytest.raises(ValueError):
        lat.histogram_quantile([0.1, 0.5], [3, 2], 0.5)
    with pytest.raises(ValueError):
        lat.histogram_quantile([0.1, 0.5], [1, 2], 1.5)


# ---------- cost ----------

PRICES = {"input": 2.0, "cached_input": 0.2, "output": 10.0}


def test_cost_per_1k_with_cached_tokens(lat):
    usages = [
        {"input_tokens": 3000, "cached_tokens": 2500, "output_tokens": 200},
        {"input_tokens": 3000, "output_tokens": 100},
    ]
    first = (500 * 2.0 + 2500 * 0.2 + 200 * 10.0) / 1e6
    second = (3000 * 2.0 + 100 * 10.0) / 1e6
    assert lat.cost_per_1k(usages, PRICES) == pytest.approx((first + second) / 2 * 1000)


def test_cost_rejects_bad_usage(lat):
    with pytest.raises(ValueError):
        lat.cost_per_1k([{"input_tokens": 10, "cached_tokens": 20, "output_tokens": 1}], PRICES)
    with pytest.raises(ValueError):
        lat.cost_per_1k([], PRICES)


# ---------- SLO ----------

def test_slo_report(lat):
    latencies = [0.5, 0.8, 1.2, 0.4, 0.3, 2.5, 0.6, 0.7, 0.9, 0.2]
    ok = [True, True, True, True, False, True, True, True, True, True]
    r = lat.slo_report(latencies, ok, threshold_s=1.0, target=0.9)
    assert r["n"] == 10 and r["bad"] == 3, "request lỗi tính là xấu dù nhanh"
    assert r["good_ratio"] == pytest.approx(0.7)
    assert r["error_budget"] == pytest.approx(0.1)
    assert r["burn_rate"] == pytest.approx(3.0)
    assert not r["met"]


def test_slo_met_at_boundary(lat):
    r = lat.slo_report([1.0] * 99 + [5.0], [True] * 100, threshold_s=1.0, target=0.99)
    assert r["met"] and r["burn_rate"] == pytest.approx(1.0), "đúng bằng ngưỡng là tốt; tiêu đúng hết ngân sách là burn rate 1"


def test_slo_rejects_bad_input(lat):
    with pytest.raises(ValueError):
        lat.slo_report([1.0], [True, False], 1.0, 0.9)
    with pytest.raises(ValueError):
        lat.slo_report([1.0], [True], 1.0, 1.0)
