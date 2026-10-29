import numpy as np
import pandas as pd
import pytest
from scipy import integrate, stats

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def bayes():
    return ex.module("bayes.py")


def test_beta_posterior(bayes):
    assert bayes.beta_posterior(2.0, 8.0, 3, 10) == pytest.approx((5.0, 15.0))
    assert bayes.beta_posterior(1.0, 1.0, 0, 7) == pytest.approx((1.0, 8.0))


@pytest.mark.parametrize("a, b, level", [(5, 15, 0.95), (1, 8, 0.9), (30.5, 209.0, 0.95)])
def test_credible_interval(bayes, a, b, level):
    lo, hi = bayes.credible_interval(a, b, level)
    assert stats.beta.cdf(lo, a, b) == pytest.approx((1 - level) / 2, abs=1e-9)
    assert stats.beta.cdf(hi, a, b) == pytest.approx(1 - (1 - level) / 2, abs=1e-9)


def test_fit_beta_prior_formula(bayes):
    k = np.array([10, 30, 5, 60])
    n = np.array([100, 150, 80, 300])
    m = k.sum() / n.sum()
    s2 = (n * (k / n - m) ** 2).sum() / n.sum()
    tau2 = s2 - m * (1 - m) * len(n) / n.sum()
    total = m * (1 - m) / tau2 - 1
    assert bayes.fit_beta_prior(k, n) == pytest.approx((m * total, (1 - m) * total))


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_fit_beta_prior_recovers_truth(bayes, seed):
    rng = np.random.default_rng(seed)
    n = rng.integers(5, 3000, 70)
    k = rng.binomial(n, rng.beta(4, 26, 70))            # prior thật: mean 0.133, a + b = 30
    a, b = bayes.fit_beta_prior(k, n)
    assert a / (a + b) == pytest.approx(4 / 30, abs=0.02)
    assert 15 <= a + b <= 60


def test_fit_beta_prior_raises_when_no_heterogeneity(bayes):
    n = np.full(50, 400)
    k = np.full(50, 52)                                  # mọi nhóm đúng 13%: không có dị biệt
    with pytest.raises(ValueError):
        bayes.fit_beta_prior(k, n)


def test_prob_greater(bayes):
    a1, b1, a2, b2 = 54.5, 290.9, 1457.5, 7854.9
    exact, _ = integrate.quad(lambda x: stats.beta.pdf(x, a1, b1) * stats.beta.cdf(x, a2, b2), 0, 1)
    assert bayes.prob_greater(a1, b1, a2, b2) == pytest.approx(exact, abs=0.005)
    assert bayes.prob_greater(10, 90, 10, 90) == pytest.approx(0.5, abs=0.005)
    assert bayes.prob_greater(3, 7, 3, 7, n_draws=1000, seed=1) == bayes.prob_greater(3, 7, 3, 7, n_draws=1000, seed=1)


def test_shrinkage_table(bayes):
    counts = pd.DataFrame({"n": [2, 1000, 50], "bad": [1, 200, 5]}, index=["tiny", "big", "mid"])
    out = bayes.shrinkage_table(counts, a=13.0, b=87.0)
    assert out.loc["tiny", "raw_rate"] == pytest.approx(0.5)
    assert out.loc["tiny", "post_mean"] == pytest.approx(14 / 102)
    assert out.loc["big", "post_mean"] == pytest.approx(213 / 1100)
    assert list(out.index) == ["big", "tiny", "mid"]    # nhóm 2 đơn không còn đứng đầu
    assert (out.ci_lo < out.post_mean).all() and (out.post_mean < out.ci_hi).all()
    assert {"n", "bad"} <= set(out.columns)


ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5", "o6"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered", "delivered"],
    "order_delivered_customer_date": ["2018-01-05", "2018-01-06", "2018-01-07", None, None, "2018-01-09"],
})
REVIEWS = pd.DataFrame({
    "order_id": ["o1", "o2", "o2", "o3", "o4", "o5", "o6"],
    "review_score": [5, 5, 1, 2, 1, 1, 4],
    "review_answer_timestamp": pd.to_datetime([
        "2018-01-06", "2018-01-07", "2018-01-09", "2018-01-08", "2018-01-02", "2018-01-03", "2018-01-10"]),
})
ITEMS = pd.DataFrame({
    "order_id": ["o1", "o2", "o2", "o3", "o4", "o5", "o6"],
    "order_item_id": [1, 1, 2, 1, 1, 1, 1],
    "product_id": ["p1", "p2", "p1", "p1", "p2", "p2", "p3"],
})
PRODUCTS = pd.DataFrame({"product_id": ["p1", "p2", "p3"], "product_category_name": ["cama", "audio_pt", None]})
TRANSLATION = pd.DataFrame({"product_category_name": ["cama", "audio_pt"], "product_category_name_english": ["bed", "audio"]})


def test_category_counts_small(bayes):
    out = bayes.category_counts(ORDERS, REVIEWS, ITEMS, PRODUCTS, TRANSLATION)
    # o1 bed 5★, o2 audio (review mới nhất 1★), o3 bed 2★; o4, o5 không giao xong; o6 không có category
    assert out.index.name == "category"
    assert list(out.index) == ["bed", "audio"]
    assert out.loc["bed", "n"] == 2 and out.loc["bed", "bad"] == 1
    assert out.loc["audio", "n"] == 1 and out.loc["audio", "bad"] == 1


def test_real_olist_categories(bayes):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_products_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    counts = bayes.category_counts(
        pd.read_csv(raw / "olist_orders_dataset.csv"),
        pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"]),
        pd.read_csv(raw / "olist_order_items_dataset.csv"),
        pd.read_csv(raw / "olist_products_dataset.csv"),
        pd.read_csv(raw / "product_category_name_translation.csv", encoding="utf-8-sig"),
    )
    assert len(counts) == 71 and counts.n.sum() == 94455
    assert counts.loc["fashion_male_clothing", "n"] == 105 and counts.loc["fashion_male_clothing", "bad"] == 24
    a, b = bayes.fit_beta_prior(counts.bad, counts.n)
    assert a / (a + b) == pytest.approx(0.1275, abs=0.0005)
    table = bayes.shrinkage_table(counts, a, b)
    assert table.index[0] == "office_furniture"
    assert table.loc["security_and_services", "post_mean"] < 0.14      # 1/2 đơn xấu → co về gần 12.8%
