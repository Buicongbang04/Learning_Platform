import numpy as np
import pandas as pd
import pytest
from scipy import stats

from testkit import ROOT, Exercise

ex = Exercise(__file__)

@pytest.fixture(scope="module")
def nb():
    return ex.notebook("distribution.ipynb")

def lognormal_sample(seed: int, n: int = 5000) -> np.ndarray:
    return np.random.default_rng(seed).lognormal(4.7, 0.8, n)


def gamma_sample(seed: int, n: int = 5000) -> np.ndarray:
    return np.random.default_rng(seed).gamma(1.5, 100, n)


def test_order_values_sums_delivered_only(nb):
    items = pd.DataFrame({
        "order_id": ["a", "a", "b", "c", "d"],
        "price": [100.0, 50.0, 30.0, 70.0, 10.0],
        "freight_value": [10.0, 5.0, 3.0, 7.0, 1.0],
    })
    orders = pd.DataFrame({
        "order_id": ["a", "b", "c", "d"],
        "order_status": ["delivered", "delivered", "canceled", "delivered"],
        "order_delivered_customer_date": pd.to_datetime(["2018-01-05", "2018-01-06", None, None]),
    })
    out = nb.order_values(items, orders)
    assert out.to_dict() == pytest.approx({"a": 165.0, "b": 33.0})

@pytest.mark.parametrize("seed", [0, 1])
def test_fit_lognormal_closed_form(nb, seed):
    x = lognormal_sample(seed)
    mu, sigma = nb.fit_lognormal(x)
    assert mu == pytest.approx(np.log(x).mean(), abs=1e-12)
    assert sigma == pytest.approx(np.log(x).std(ddof=0), abs=1e-12)
    s_ref, _, scale_ref = stats.lognorm.fit(x, floc=0)
    assert (mu, sigma) == pytest.approx((np.log(scale_ref), s_ref), rel=1e-4)

@pytest.mark.parametrize("seed", [2, 3])
def test_fit_gamma(nb, seed):
    x = gamma_sample(seed)
    shape, scale = nb.fit_gamma(x)
    a_ref, _, scale_ref = stats.gamma.fit(x, floc=0)
    assert (shape, scale) == pytest.approx((a_ref, scale_ref), rel=1e-3)
    assert shape == pytest.approx(1.5, rel=0.08)
    assert shape * scale == pytest.approx(x.mean(), rel=1e-3)     # MLE gamma giữ đúng trung bình mẫu

@pytest.mark.parametrize("seed", [4, 5, 6])
def test_compare_fits_picks_true_distribution(nb, seed):
    t_ln = nb.compare_fits(lognormal_sample(seed))
    t_g = nb.compare_fits(gamma_sample(seed))
    assert list(t_ln.index) == ["lognorm", "gamma"]
    assert list(t_ln.columns) == ["loglik", "aic", "ks_stat", "p_exceed"]
    assert t_ln.loc["lognorm", "aic"] < t_ln.loc["gamma", "aic"]
    assert t_g.loc["gamma", "aic"] < t_g.loc["lognorm", "aic"]
    assert t_ln.loc["lognorm", "ks_stat"] < t_ln.loc["gamma", "ks_stat"]

def test_compare_fits_values(nb):
    x = lognormal_sample(7)
    t = nb.compare_fits(x, threshold=500)
    mu, sigma = np.log(x).mean(), np.log(x).std()
    ll = stats.lognorm.logpdf(x, sigma, scale=np.exp(mu)).sum()
    assert t.loc["lognorm", "loglik"] == pytest.approx(ll, rel=1e-9)
    assert (t.aic == 4 - 2 * t.loglik).all()
    assert t.loc["lognorm", "ks_stat"] == pytest.approx(
        stats.kstest(x, "lognorm", args=(sigma, 0, np.exp(mu))).statistic, abs=1e-9)
    assert t.loc["lognorm", "p_exceed"] == pytest.approx(stats.lognorm.sf(500, sigma, scale=np.exp(mu)), rel=1e-9)

def test_qq_points(nb):
    x = lognormal_sample(8, n=2000)
    th, s = nb.qq_points(x, "lognorm", (4.7, 0.8))
    assert len(th) == len(s) == len(x)
    assert np.all(np.diff(s) >= 0) and np.all(np.diff(th) > 0)
    assert th[0] == pytest.approx(stats.lognorm.ppf(0.5 / 2000, 0.8, scale=np.exp(4.7)))
    assert np.corrcoef(np.log(th), np.log(s))[0, 1] > 0.99
    th_g, _ = nb.qq_points(x, "gamma", (1.5, 100))
    assert th_g[-1] == pytest.approx(stats.gamma.ppf(1 - 0.5 / 2000, 1.5, scale=100))

def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=["order_delivered_customer_date"])
    x = nb.order_values(items, orders).to_numpy()
    assert len(x) == 96470
    assert nb.fit_lognormal(x) == pytest.approx((4.691, 0.808), abs=1e-3)
    t = nb.compare_fits(x)
    assert t.loc["lognorm", "aic"] < t.loc["gamma", "aic"]
    assert t.loc["lognorm", "p_exceed"] == pytest.approx(0.0030, abs=2e-4)
    assert t.loc["lognorm", "p_exceed"] < (x > 1000).mean() / 3           # lognormal đánh giá thấp đuôi
