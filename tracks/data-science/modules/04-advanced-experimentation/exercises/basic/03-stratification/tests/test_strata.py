import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def st():
    return ex.module("strata.py")


def make_population(n: int, seed: int):
    """4 tầng (strata) có mức metric rất khác nhau, như 4 loại cửa hàng hay 4 nhóm chi tiêu."""
    rng = np.random.default_rng(seed)
    strata = rng.choice(np.array(["S", "M", "L", "XL"]), n, p=[0.4, 0.3, 0.2, 0.1])
    level = {"S": 10.0, "M": 30.0, "L": 60.0, "XL": 120.0}
    y0 = np.array([level[s] for s in strata]) + rng.normal(0, 8, n)
    return y0, strata


def test_quantile_strata(st):
    x = np.arange(100, dtype=float)[::-1]
    labels = st.strata_from_quantiles(x, 4)
    assert sorted(set(labels.tolist())) == [0, 1, 2, 3]
    assert np.bincount(labels).tolist() == [25, 25, 25, 25]
    assert labels[0] == 3 and labels[-1] == 0   # giá trị lớn nhất ở tầng cao nhất


def test_assignment_is_balanced_within_each_stratum(st):
    _, strata = make_population(1001, seed=1)
    treat = st.stratified_assign(strata, seed=0)
    assert treat.dtype == bool and treat.shape == strata.shape
    for s in np.unique(strata):
        in_s = strata == s
        assert abs(treat[in_s].sum() - (~treat[in_s]).sum()) <= 1


def test_assignment_reproducible_and_random(st):
    _, strata = make_population(500, seed=2)
    a = st.stratified_assign(strata, seed=7)
    assert np.array_equal(a, st.stratified_assign(strata, seed=7))
    assert not np.array_equal(a, st.stratified_assign(strata, seed=8))
    # mỗi đơn vị vào treatment khoảng một nửa số lần; nhánh nhận đơn vị lẻ cũng phải ngẫu nhiên
    odd = np.repeat(np.arange(50), 3)   # 50 tầng, mỗi tầng 3 đơn vị
    share = np.mean([st.stratified_assign(odd, seed=s) for s in range(200)], axis=0)
    assert 0.4 < share.mean() < 0.6
    assert share.min() > 0.3 and share.max() < 0.7


def test_post_stratified_matches_simple_with_one_stratum(st):
    rng = np.random.default_rng(3)
    y = rng.normal(0, 1, 400)
    treat = rng.permutation(np.arange(400) % 2 == 0)
    out = st.post_stratified_effect(y, treat, np.zeros(400))
    assert out["diff"] == pytest.approx(y[treat].mean() - y[~treat].mean())
    se = np.sqrt(y[treat].var(ddof=1) / 200 + y[~treat].var(ddof=1) / 200)
    assert out["se"] == pytest.approx(se)


def test_post_stratified_hand_example(st):
    y = np.array([1, 3, 5, 7, 10, 12, 14, 11, 13, 15, 17], dtype=float)
    treat = np.array([0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1], dtype=bool)
    strata = np.array(["a"] * 4 + ["b"] * 7)
    out = st.post_stratified_effect(y, treat, strata)
    assert out["diff"] == pytest.approx((4 * 4 + 7 * 2) / 11)
    assert out["se"] == pytest.approx(np.sqrt((4 / 11) ** 2 * 2 + (7 / 11) ** 2 * 3))
    assert out["ci_low"] < out["diff"] < out["ci_high"]


def test_too_few_units_raise(st):
    with pytest.raises(ValueError):
        st.post_stratified_effect(np.array([1.0, 2, 3, 4, 5]), np.array([1, 0, 0, 1, 0], bool),
                                  np.array([0, 0, 0, 1, 1]))


def test_post_stratification_reduces_variance_without_bias(st):
    est_simple, est_post, hits = [], [], 0
    for seed in range(300):
        y0, strata = make_population(2000, seed=100 + seed)
        rng = np.random.default_rng(seed)
        treat = rng.random(2000) < 0.5          # random đơn giản, không phân tầng
        y = y0 + 2.0 * treat
        out = st.post_stratified_effect(y, treat, strata)
        est_post.append(out["diff"])
        est_simple.append(y[treat].mean() - y[~treat].mean())
        hits += out["ci_low"] <= 2.0 <= out["ci_high"]
    assert np.mean(est_post) == pytest.approx(2.0, abs=0.15)
    assert np.std(est_post) < 0.4 * np.std(est_simple)
    assert 0.91 <= hits / 300 <= 0.99
