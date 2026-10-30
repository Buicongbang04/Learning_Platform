import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("weighted_stats.ipynb")


X = [3.0, 1.0, 7.0, 2.0, 5.0]
W = [2, 1, 1, 3, 4]


def expanded():
    return np.repeat(X, W)


def test_weighted_mean_basic(nb):
    assert nb.weighted_mean([1, 2, 3], [1, 1, 2]) == pytest.approx(2.25)
    assert nb.weighted_mean(X, W) == pytest.approx(expanded().mean())
    assert isinstance(nb.weighted_mean(X, W), float)


def test_weighted_mean_accepts_series_and_drops_nan(nb):
    x = pd.Series([1.0, np.nan, 3.0, 10.0], index=[10, 11, 12, 13])
    w = pd.Series([1.0, 5.0, 1.0, np.nan], index=[10, 11, 12, 13])
    assert nb.weighted_mean(x, w) == pytest.approx(2.0)


def test_weighted_mean_equal_weights_is_mean(nb):
    assert nb.weighted_mean(X, [1] * 5) == pytest.approx(np.mean(X))
    assert nb.weighted_mean(X, [0.5] * 5) == pytest.approx(np.mean(X))


@pytest.mark.parametrize("x, w", [([1, 2], [1]), ([1, 2], [1, -1]), ([1, 2], [0, 0]), ([np.nan, 2], [1, 0])])
def test_weighted_mean_rejects_bad_input(nb, x, w):
    with pytest.raises(ValueError):
        nb.weighted_mean(x, w)


def test_weighted_std_matches_expanded(nb):
    assert nb.weighted_std(X, W) == pytest.approx(pd.Series(expanded()).std())
    assert nb.weighted_std(X, W, ddof=0) == pytest.approx(np.std(expanded()))
    assert nb.weighted_std(X, W) > nb.weighted_std(X, W, ddof=0)


def test_weighted_std_rejects_bad_input(nb):
    with pytest.raises(ValueError):
        nb.weighted_std([1, 2, 3], [1, 2])


@pytest.mark.parametrize("q", [0.0, 0.1, 0.25, 0.5, 0.6, 0.75, 0.9, 1.0])
def test_weighted_quantile_matches_inverted_cdf(nb, q):
    assert nb.weighted_quantile(X, W, q) == pytest.approx(np.quantile(expanded(), q, method="inverted_cdf"))


def test_weighted_quantile_fractional_and_zero_weights(nb):
    # cộng dồn 0.2, 0.5, 1.0: median là giá trị đầu tiên có cộng dồn >= 0.5
    assert nb.weighted_quantile([3.0, 1.0, 2.0], [0.5, 0.2, 0.3], 0.5) == 2.0
    # giá trị có trọng số 0 không bao giờ là kết quả, kể cả ở q = 0
    assert nb.weighted_quantile([0.0, 1.0, 2.0], [0, 1, 1], 0.0) == 1.0
    with pytest.raises(ValueError):
        nb.weighted_quantile([1.0, 2.0], [1, 1], 1.5)


def test_functions_do_not_mutate_input(nb):
    x = pd.Series([5.0, 1.0, 3.0])
    w = pd.Series([1.0, 2.0, 3.0])
    nb.weighted_mean(x, w)
    nb.weighted_std(x, w)
    nb.weighted_quantile(x, w, 0.5)
    assert x.tolist() == [5.0, 1.0, 3.0] and w.tolist() == [1.0, 2.0, 3.0]


def test_real_telco_frequency_table(nb):
    telco = pd.read_csv(ex.dataset("telco-churn") / "WA_Fn-UseC_-Telco-Customer-Churn.csv")
    freq = telco["tenure"].value_counts()
    assert nb.weighted_mean(freq.index, freq.values) == pytest.approx(32.3711, abs=1e-4)
    assert nb.weighted_std(freq.index, freq.values) == pytest.approx(24.5595, abs=1e-4)
    assert [nb.weighted_quantile(freq.index, freq.values, q) for q in (0.25, 0.5, 0.75)] == [9.0, 29.0, 55.0]


def test_real_rossmann_sales_per_customer(nb):
    train = pd.read_csv(ex.dataset("store-sales") / "train.csv", usecols=["Open", "Sales", "Customers"])
    days = train[(train.Open == 1) & (train.Sales > 0)]
    ratio = days.Sales / days.Customers
    assert nb.weighted_mean(ratio, days.Customers) == pytest.approx(9.1193, abs=1e-4)
    assert nb.weighted_quantile(ratio, days.Customers, 0.5) == pytest.approx(8.8614, abs=1e-4)
