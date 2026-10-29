import numpy as np
import pandas as pd
import pytest
from scipy import stats

from testkit import ROOT, Exercise

ex = Exercise(__file__)

COLUMNS = ["dist", "loglik", "n_params", "aic", "q95"]
DISTS = {"expon": stats.expon, "gamma": stats.gamma, "lognorm": stats.lognorm, "weibull_min": stats.weibull_min}


@pytest.fixture(scope="module")
def fit():
    return ex.module("fit.py")


def test_structure(fit):
    x = np.random.default_rng(0).lognormal(2.3, 0.7, 3000)
    table = fit.fit_candidates(x)
    assert list(table.columns) == COLUMNS
    assert set(table.dist) == set(DISTS)
    assert table.aic.is_monotonic_increasing
    assert dict(zip(table.dist, table.n_params)) == {"expon": 1, "gamma": 2, "lognorm": 2, "weibull_min": 2}


def test_aic_and_loglik_consistent(fit):
    x = np.random.default_rng(1).gamma(3.0, 4.0, 2000)
    table = fit.fit_candidates(x).set_index("dist")
    assert np.allclose(table.aic, 2 * table.n_params - 2 * table.loglik)
    # loglik phải là log-likelihood tại MLE (loc cố định 0): không thấp hơn MLE của scipy
    for name, dist in DISTS.items():
        params = dist.fit(x, floc=0)
        assert table.loc[name, "loglik"] == pytest.approx(dist.logpdf(x, *params).sum(), abs=0.5)


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_picks_true_family(fit, seed):
    rng = np.random.default_rng(seed)
    assert fit.fit_candidates(rng.lognormal(2.3, 0.7, 4000)).dist.iloc[0] == "lognorm"
    assert fit.fit_candidates(rng.exponential(12.0, 4000)).dist.iloc[0] in {"expon", "gamma", "weibull_min"}
    assert fit.fit_candidates(rng.weibull(1.5, 4000) * 14).dist.iloc[0] == "weibull_min"


def test_q95_from_fitted_model(fit):
    x = np.random.default_rng(5).lognormal(2.3, 0.7, 5000)
    table = fit.fit_candidates(x).set_index("dist")
    assert table.loc["lognorm", "q95"] == pytest.approx(np.exp(2.3 + 1.6449 * 0.7), rel=0.03)


def test_quantile_ci(fit):
    x = np.random.default_rng(6).lognormal(2.3, 0.7, 2000)
    est, lo, hi = fit.quantile_ci(x, 0.95, n_boot=1000, seed=0)
    assert est == pytest.approx(np.quantile(x, 0.95))
    assert lo < est < hi
    assert lo < np.exp(2.3 + 1.6449 * 0.7) < hi
    assert fit.quantile_ci(x, 0.95, n_boot=500, seed=2) == fit.quantile_ci(x, 0.95, n_boot=500, seed=2)
    _, lo90, hi90 = fit.quantile_ci(x, 0.9, n_boot=1000, seed=0)
    assert lo90 < lo and hi90 < hi                             # q90 nằm thấp hơn q95


def test_real_olist_delivery_days(fit):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    d = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    days = ((d.order_delivered_customer_date - d.order_purchase_timestamp).dt.total_seconds() / 86400).to_numpy()
    table = fit.fit_candidates(days).set_index("dist")
    assert table.index[0] == "lognorm"
    # mô hình có AIC tốt nhất vẫn lệch ở đuôi: q95 của lognormal cao hơn q95 thực nghiệm (29.3 ngày)
    assert table.loc["lognorm", "q95"] == pytest.approx(30.72, abs=0.05)
    est, lo, hi = fit.quantile_ci(days, 0.95, n_boot=300, seed=0)
    assert est == pytest.approx(29.27, abs=0.01) and hi < table.loc["lognorm", "q95"]


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 300
