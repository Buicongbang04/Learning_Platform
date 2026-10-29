import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def survey():
    return ex.module("survey.py")


def make_population(seed: int, n: int = 40_000) -> pd.DataFrame:
    """Tổng thể: 3 vùng có tỉ lệ review xấu khác nhau; đơn trễ xấu nhiều hơn hẳn."""
    rng = np.random.default_rng(seed)
    region = rng.choice(["SE", "NE", "S"], n, p=[0.7, 0.1, 0.2])
    late = rng.random(n) < np.where(region == "NE", 0.2, 0.07)
    p_bad = np.where(late, 0.54, 0.09) + np.where(region == "NE", 0.03, 0.0)
    return pd.DataFrame({"region": region, "late": late, "bad": (rng.random(n) < p_bad).astype(int)})


def biased_sample(pop: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    """Khảo sát gọi điện: khách có đơn trễ nghe máy nhiều gấp 6 lần (chọn mẫu phụ thuộc biến quan sát được)."""
    p = np.where(pop.late, 0.6, 0.1)
    keep = np.random.default_rng(seed + 1000).random(len(pop)) < p
    return pop[keep].copy(), p[keep]


def test_poststratified_mean_small(survey):
    sample = pd.DataFrame({"g": ["a", "a", "b", "b", "b", "b"], "y": [1, 0, 1, 1, 1, 0]})
    shares = pd.Series({"a": 0.8, "b": 0.2})
    assert survey.poststratified_mean(sample, "y", "g", shares) == pytest.approx(0.8 * 0.5 + 0.2 * 0.75)


def test_poststratified_mean_normalises_shares(survey):
    sample = pd.DataFrame({"g": ["a", "b"], "y": [1.0, 0.0]})
    assert survey.poststratified_mean(sample, "y", "g", pd.Series({"a": 300, "b": 100})) == pytest.approx(0.75)


def test_missing_stratum_raises(survey):
    sample = pd.DataFrame({"g": ["a", "a"], "y": [1, 0]})
    with pytest.raises(ValueError):
        survey.poststratified_mean(sample, "y", "g", pd.Series({"a": 0.5, "b": 0.5}))


@pytest.mark.parametrize("seed", range(10))
def test_poststratification_removes_selection_bias(survey, seed):
    pop = make_population(seed)
    sample, _ = biased_sample(pop, seed)
    truth = pop.bad.mean()
    shares = pop.late.value_counts(normalize=True)
    assert sample.bad.mean() - truth > 0.08                    # trung bình thô lệch mạnh
    assert survey.poststratified_mean(sample, "bad", "late", shares) == pytest.approx(truth, abs=0.02)


@pytest.mark.parametrize("seed", range(5))
def test_ipw_mean_with_known_probabilities(survey, seed):
    pop = make_population(seed)
    sample, p = biased_sample(pop, seed)
    assert survey.ipw_mean(sample.bad, p) == pytest.approx(pop.bad.mean(), abs=0.02)


def test_ipw_equals_plain_mean_with_constant_probability(survey):
    y = np.array([1, 0, 0, 1, 1.0])
    assert survey.ipw_mean(y, np.full(5, 0.3)) == pytest.approx(0.6)


def test_bootstrap_ci_covers_truth(survey):
    hits = 0
    for seed in range(40):
        pop = make_population(seed, n=20_000)
        sample, _ = biased_sample(pop, seed)
        shares = pop.late.value_counts(normalize=True)
        est, lo, hi = survey.poststrat_bootstrap_ci(sample, "bad", "late", shares, n_boot=500, seed=seed)
        assert lo < est < hi
        assert est == pytest.approx(survey.poststratified_mean(sample, "bad", "late", shares))
        hits += lo <= pop.bad.mean() <= hi
    assert hits >= 33                                          # kỳ vọng ~38/40 với CI 95%


def test_real_olist_late_oversampled(survey):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    d = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()].copy()
    d["late"] = d.order_delivered_customer_date > d.order_estimated_delivery_date
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    pop = d.merge(latest[["order_id", "review_score"]], on="order_id")
    pop["bad"] = (pop.review_score <= 2).astype(int)
    assert pop.bad.mean() == pytest.approx(0.128, abs=0.001)
    p = np.where(pop.late, 0.5, 0.05)
    sample = pop[np.random.default_rng(0).random(len(pop)) < p]
    shares = pop.late.value_counts(normalize=True)
    assert sample.bad.mean() > 0.2
    assert survey.poststratified_mean(sample, "bad", "late", shares) == pytest.approx(0.128, abs=0.01)


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 300
