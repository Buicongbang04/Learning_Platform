import math

import pytest

from testkit import Exercise

ex = Exercise(__file__)

RECS = ["a", "b", "c", "d", "e"]
RELEVANT = {"b", "d", "x"}


@pytest.fixture(scope="module")
def rk():
    return ex.module("ranking.py")


def test_precision_at_k(rk):
    assert rk.precision_at_k(RECS, RELEVANT, 5) == pytest.approx(2 / 5)
    assert rk.precision_at_k(RECS, RELEVANT, 3) == pytest.approx(1 / 3)
    assert rk.precision_at_k(RECS, RELEVANT, 1) == 0.0


def test_precision_divides_by_k_even_for_short_lists(rk):
    assert rk.precision_at_k(["b"], RELEVANT, 3) == pytest.approx(1 / 3)


def test_recall_at_k(rk):
    assert rk.recall_at_k(RECS, RELEVANT, 5) == pytest.approx(2 / 3)
    assert rk.recall_at_k(RECS, RELEVANT, 2) == pytest.approx(1 / 3)
    assert rk.recall_at_k(RECS, set(), 5) == 0.0


def test_average_precision_at_k(rk):
    # hit ở vị trí 2 (precision 1/2) và 4 (precision 2/4), chia cho min(3, 5)
    assert rk.average_precision_at_k(RECS, RELEVANT, 5) == pytest.approx((1 / 2 + 2 / 4) / 3)
    # k = 2: chỉ hit ở vị trí 2, chia cho min(3, 2) = 2
    assert rk.average_precision_at_k(RECS, RELEVANT, 2) == pytest.approx((1 / 2) / 2)
    assert rk.average_precision_at_k(["b", "d"], {"b", "d"}, 5) == pytest.approx(1.0)
    assert rk.average_precision_at_k(RECS, set(), 5) == 0.0


def test_average_precision_rewards_putting_hits_first(rk):
    early = rk.average_precision_at_k(["b", "d", "a"], {"b", "d"}, 3)
    late = rk.average_precision_at_k(["a", "b", "d"], {"b", "d"}, 3)
    assert early == pytest.approx(1.0)
    assert late == pytest.approx((1 / 2 + 2 / 3) / 2)
    # precision@3 không phân biệt được hai thứ tự này
    assert rk.precision_at_k(["b", "d", "a"], {"b", "d"}, 3) == rk.precision_at_k(["a", "b", "d"], {"b", "d"}, 3)


def test_ndcg_at_k(rk):
    dcg = 1 / math.log2(3) + 1 / math.log2(5)
    idcg = 1 + 1 / math.log2(3) + 1 / math.log2(4)
    assert rk.ndcg_at_k(RECS, RELEVANT, 5) == pytest.approx(dcg / idcg)
    assert rk.ndcg_at_k(["b", "d", "a"], {"b", "d"}, 3) == pytest.approx(1.0)
    assert rk.ndcg_at_k(["a", "c"], {"b"}, 2) == 0.0
    assert rk.ndcg_at_k(RECS, set(), 5) == 0.0


def test_ndcg_ideal_is_capped_at_k(rk):
    # 5 item relevant nhưng chỉ xét k = 2: hai hit đầu là hoàn hảo
    assert rk.ndcg_at_k(["p", "q"], {"p", "q", "r", "s", "t"}, 2) == pytest.approx(1.0)


def test_mean_at_k_over_truth_users(rk):
    recs = {1: ["a", "b"], 2: ["c", "d"], 99: ["z"]}
    truth = {1: {"a"}, 2: {"x"}, 3: {"a"}}
    # user 3 không có gợi ý → 0; user 99 không có trong truth → bỏ qua
    assert rk.mean_at_k(recs, truth, rk.precision_at_k, 2) == pytest.approx((1 / 2 + 0 + 0) / 3)
    assert rk.mean_at_k(recs, truth, rk.recall_at_k, 2) == pytest.approx((1 + 0 + 0) / 3)
