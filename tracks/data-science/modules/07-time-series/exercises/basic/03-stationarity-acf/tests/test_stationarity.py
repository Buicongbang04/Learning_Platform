import warnings

import numpy as np
import pytest
from statsmodels.tsa.stattools import acf, adfuller, kpss

from testkit import Exercise

ex = Exercise(__file__)
SEEDS = range(5)


@pytest.fixture(scope="module")
def stt():
    return ex.module("stationarity.py")


def white_noise(seed, n=1000):
    return np.random.default_rng(seed).normal(0, 1, n)


def random_walk(seed, n=1000):
    return np.cumsum(np.random.default_rng(seed).normal(0, 1, n))


def test_difference(stt):
    y = np.array([3.0, 5.0, 4.0, 8.0, 9.0])
    np.testing.assert_allclose(stt.difference(y), [2, -1, 4, 1])
    np.testing.assert_allclose(stt.difference(y, lag=2), [1, 3, 5])


@pytest.mark.parametrize("lag", [1, 7])
def test_inverse_difference_roundtrip(stt, lag):
    y = np.cumsum(np.random.default_rng(0).normal(5, 2, 40))
    history, future = y[:30], y[30:]
    d_future = stt.difference(y, lag)[30 - lag:]       # sai phân của 10 điểm tương lai
    np.testing.assert_allclose(stt.inverse_difference(d_future, history, lag), future)


def test_inverse_difference_constant_forecast(stt):
    # dự báo sai phân = 2 mỗi bước → mức tăng tuyến tính từ quan sát cuối
    np.testing.assert_allclose(stt.inverse_difference(np.full(3, 2.0), np.array([1.0, 4.0]), 1), [6, 8, 10])


@pytest.mark.parametrize("seed", SEEDS)
def test_acf_matches_statsmodels(stt, seed):
    y = random_walk(seed, 300) + np.tile([5.0, 0, 0, 0, 0, -3, -2], 43)[:300]
    np.testing.assert_allclose(stt.acf(y, 14), acf(y, nlags=14), atol=1e-10)


def test_acf_of_weekly_pattern_peaks_at_7(stt):
    rng = np.random.default_rng(1)
    y = np.tile([30.0, 28, 27, 25, 22, 10, 12], 30) + rng.normal(0, 1, 210)
    r = stt.acf(y, 14)
    assert r[0] == pytest.approx(1.0)
    assert np.argmax(r[1:]) + 1 in (7, 14)


@pytest.mark.parametrize("adf_p, kpss_p, expected", [
    (0.01, 0.10, "stationary"),
    (0.40, 0.01, "non_stationary"),
    (0.40, 0.10, "trend_stationary"),
    (0.01, 0.01, "difference_stationary"),
])
def test_verdict_four_cases(stt, adf_p, kpss_p, expected):
    assert stt.verdict(adf_p, kpss_p) == expected


def test_verdict_respects_alpha(stt):
    assert stt.verdict(0.03, 0.10, alpha=0.01) == "trend_stationary"


@pytest.mark.parametrize("seed", SEEDS)
def test_report_matches_statsmodels(stt, seed):
    y = random_walk(seed, 400)
    rep = stt.stationarity_report(y)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        adf_p = adfuller(y, autolag="AIC", result_object=False)[1]
        kpss_p = kpss(y, regression="c", nlags="auto", result_object=False)[1]
    assert rep["adf_p"] == pytest.approx(adf_p)
    assert rep["kpss_p"] == pytest.approx(kpss_p)
    assert rep["verdict"] == stt.verdict(adf_p, kpss_p)


# Mỗi kiểm định sai 5% số lần theo thiết kế, nên không đòi đúng ở mọi seed: đòi đúng ở đa số.
# (Bản tham chiếu trên 10 khối 20 seed: thấp nhất 16/20 cho mỗi kiểm tra.)
MANY = range(20)


def test_random_walk_is_non_stationary_most_of_the_time(stt):
    hits = sum(stt.stationarity_report(random_walk(s))["verdict"] == "non_stationary" for s in MANY)
    assert hits >= 15


def test_white_noise_is_stationary_most_of_the_time(stt):
    hits = sum(stt.stationarity_report(white_noise(s))["verdict"] == "stationary" for s in MANY)
    assert hits >= 15


def test_n_diffs_most_of_the_time(stt):
    assert sum(stt.n_diffs(white_noise(s)) == 0 for s in MANY) >= 15
    assert sum(stt.n_diffs(random_walk(s)) == 1 for s in MANY) >= 15
    assert sum(stt.n_diffs(np.cumsum(random_walk(s))) == 2 for s in MANY) >= 15
