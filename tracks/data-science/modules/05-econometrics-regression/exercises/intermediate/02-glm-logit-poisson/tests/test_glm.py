import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
import statsmodels.formula.api as smf

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def glm():
    return ex.module("glm.py")


def logit_data(seed: int, n: int = 20000) -> pd.DataFrame:
    """Giống bài toán review xấu: late tăng log-odds 2.5, log_value tăng 0.1."""
    rng = np.random.default_rng(seed)
    late = (rng.random(n) < 0.08).astype(int)
    log_value = rng.normal(4.7, 0.8, n)
    eta = -2.8 + 2.5 * late + 0.1 * log_value
    bad = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(int)
    return pd.DataFrame({"bad": bad, "late": late, "log_value": log_value})


def count_data(seed: int, alpha: float, n: int = 20000) -> pd.DataFrame:
    """Số món thêm: mean = exp(-0.3 - 0.4 x). alpha = 0 là Poisson, alpha > 0 là Negative Binomial."""
    rng = np.random.default_rng(seed)
    x = rng.normal(4.2, 1, n)
    mu = np.exp(1.0 - 0.4 * x)
    if alpha == 0:
        y = rng.poisson(mu)
    else:
        y = rng.poisson(mu * rng.gamma(1 / alpha, alpha, n))   # Poisson-Gamma mixture = NB2
    return pd.DataFrame({"extra": y, "x": x})


def test_odds_ratios(glm):
    df = logit_data(0)
    res = smf.logit("bad ~ late + log_value", df).fit(disp=0)
    out = glm.odds_ratios(res)
    assert list(out.columns) == ["odds_ratio", "ci_low", "ci_high"]
    assert list(out.index) == ["Intercept", "late", "log_value"]
    assert out.odds_ratio.to_numpy() == pytest.approx(np.exp(res.params.to_numpy()))
    assert out.loc["late", "ci_low"] < np.exp(2.5) < out.loc["late", "ci_high"]
    wide = glm.odds_ratios(res, alpha=0.01)
    assert wide.loc["late", "ci_low"] < out.loc["late", "ci_low"]


@pytest.mark.parametrize("seed", [1, 2])
def test_discrete_ame_matches_statsmodels_dummy(glm, seed):
    df = logit_data(seed)
    res = smf.logit("bad ~ late + log_value", df).fit(disp=0)
    ref = res.get_margeff(dummy=True).margeff[0]          # late là biến đầu tiên
    assert glm.discrete_ame(res, df, "late") == pytest.approx(ref, abs=1e-10)
    # khác hẳn đạo hàm (coi late là biến liên tục)
    assert glm.discrete_ame(res, df, "late") > res.get_margeff().margeff[0] * 1.3


def test_discrete_ame_equals_raw_difference_without_controls(glm):
    df = logit_data(3)
    res = smf.logit("bad ~ late", df).fit(disp=0)
    raw = df[df.late == 1].bad.mean() - df[df.late == 0].bad.mean()
    assert glm.discrete_ame(res, df, "late") == pytest.approx(raw, abs=1e-8)


@pytest.mark.parametrize("seed", [4, 5, 6])
def test_dispersion(glm, seed):
    pois = smf.glm("extra ~ x", count_data(seed, 0), family=sm.families.Poisson()).fit()
    over = smf.glm("extra ~ x", count_data(seed, 2.0), family=sm.families.Poisson()).fit()
    assert glm.pearson_dispersion(pois) == pytest.approx(pois.pearson_chi2 / pois.df_resid)
    assert 0.9 < glm.pearson_dispersion(pois) < 1.1
    assert glm.pearson_dispersion(over) > 1.5


@pytest.mark.parametrize("seed", [7, 8])
def test_fit_count_model_chooses(glm, seed):
    res, kind = glm.fit_count_model("extra ~ x", count_data(seed, 0))
    assert kind == "poisson"
    assert res.params["x"] == pytest.approx(-0.4, abs=0.05)
    res, kind = glm.fit_count_model("extra ~ x", count_data(seed, 2.0))
    assert kind == "negbin"
    assert res.params["x"] == pytest.approx(-0.4, abs=0.08)
    assert "alpha" in res.params.index


def test_real_olist(glm):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv",
                         parse_dates=["order_delivered_customer_date", "order_estimated_delivery_date"])
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    rev = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    o = delivered.merge(rev[["order_id", "review_score"]], on="order_id")
    o = o.assign(bad=(o.review_score <= 2).astype(int),
                 late=(o.order_delivered_customer_date > o.order_estimated_delivery_date).astype(int))
    res = smf.logit("bad ~ late", o).fit(disp=0)
    assert glm.odds_ratios(res).loc["late", "odds_ratio"] == pytest.approx(11.59, abs=0.05)
    assert glm.discrete_ame(res, o, "late") == pytest.approx(0.449, abs=0.002)

    ov = items.groupby("order_id").agg(n_items=("order_item_id", "size"), mean_price=("price", "mean"))
    ov = ov[ov.index.isin(delivered.order_id)].assign(extra=lambda t: t.n_items - 1,
                                                      log_mean_price=lambda t: np.log(t.mean_price))
    pois = smf.glm("extra ~ log_mean_price", ov, family=sm.families.Poisson()).fit()
    assert glm.pearson_dispersion(pois) == pytest.approx(1.98, abs=0.01)
    _, kind = glm.fit_count_model("extra ~ log_mean_price", ov)
    assert kind == "negbin"
