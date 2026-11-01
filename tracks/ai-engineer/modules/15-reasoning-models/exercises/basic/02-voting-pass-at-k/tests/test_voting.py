import itertools
import math
import random

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def v():
    return ex.module("voting.py")


def test_majority_vote_basic(v):
    assert v.majority_vote(["18", "20", "18", None, "18"]) == "18"
    assert v.majority_vote(["5"]) == "5"


def test_majority_vote_ignores_none(v):
    assert v.majority_vote([None, None, "7", None]) == "7", "None (không đọc được đáp số) không phải một phiếu"
    assert v.majority_vote([None, None]) is None
    assert v.majority_vote([]) is None


def test_majority_vote_tie_goes_to_first_seen(v):
    assert v.majority_vote(["3", "9", "9", "3"]) == "3"
    assert v.majority_vote(["9", "3", "3", "9"]) == "9"
    assert v.majority_vote([None, "12", "4", "4", "12"]) == "12"
    assert v.majority_vote(["2", "10", "1"]) == "2", "hoà theo thứ tự xuất hiện, không theo thứ tự chuỗi hay giá trị"


def test_weighted_vote(v):
    answers = ["18", "20", "20", None]
    assert v.weighted_vote(answers, [0.9, 0.3, 0.4, 5.0]) == "18"
    assert v.weighted_vote(answers, [0.5, 0.3, 0.4, 0.0]) == "20"
    assert v.weighted_vote(["1", "2"], [0.5, 0.5]) == "1"
    assert v.weighted_vote([None], [1.0]) is None
    with pytest.raises(ValueError):
        v.weighted_vote(["1", "2"], [1.0])


def test_best_of_n(v):
    assert v.best_of_n(["18", "20", "7"], [0.1, 0.8, 0.5]) == "20"
    assert v.best_of_n(["18", "20", "7"], [-3.0, -1.5, -1.5]) == "20", "hoà: lời giải đứng trước"
    assert v.best_of_n([None, "4"], [0.9, 0.1]) is None, "lời giải điểm cao nhất không có đáp số thì kết quả là None"
    assert v.best_of_n([], []) is None
    with pytest.raises(ValueError):
        v.best_of_n(["1"], [0.1, 0.2])


def _pass_at_k_enumerate(n, c, k):
    pool = [1] * c + [0] * (n - c)
    subsets = list(itertools.combinations(range(n), k))
    return sum(any(pool[i] for i in s) for s in subsets) / len(subsets)


@pytest.mark.parametrize("n, c, k", [(5, 1, 1), (5, 1, 2), (6, 2, 3), (8, 0, 4), (8, 3, 5), (4, 4, 1), (7, 3, 7)])
def test_pass_at_k_matches_enumeration(v, n, c, k):
    assert v.pass_at_k(n, c, k) == pytest.approx(_pass_at_k_enumerate(n, c, k), abs=1e-12)


def test_pass_at_k_large_n_is_stable(v):
    value = v.pass_at_k(1000, 7, 100)
    expected = 1 - math.comb(993, 100) / math.comb(1000, 100)
    assert value == pytest.approx(expected, rel=1e-9)
    assert isinstance(v.pass_at_k(200, 3, 10), float)


def test_pass_at_k_is_not_the_naive_formula(v):
    # 1 - (1 - c/n)^k coi như lấy mẫu có hoàn lại: chệch so với k lời giải khác nhau
    assert v.pass_at_k(4, 2, 2) == pytest.approx(5 / 6)
    assert v.pass_at_k(4, 2, 2) != pytest.approx(1 - (1 - 2 / 4) ** 2)


def test_pass_at_k_rejects_bad_arguments(v):
    for args in [(4, 5, 1), (4, 1, 0), (4, 1, 5), (4, -1, 1)]:
        with pytest.raises(ValueError):
            v.pass_at_k(*args)


def test_maj_at_k_blocks(v):
    samples = [["1", "2", "2", "2", "1", "1"], ["5", None, "5", "6", "6", "6"]]
    golds = ["2", "5"]
    assert v.maj_at_k(samples, golds, 1) == pytest.approx((3 / 6 + 2 / 6) / 2)
    # k = 2: khối (1,2)(2,2)(1,1) -> 1, 2, 1 ; (5,None)(5,6)(6,6) -> 5, 5, 6
    assert v.maj_at_k(samples, golds, 2) == pytest.approx((1 / 3 + 2 / 3) / 2)
    # k = 3: khối (1,2,2)(2,1,1) -> 2, 1 ; (5,None,5)(6,6,6) -> 5, 6
    assert v.maj_at_k(samples, golds, 3) == pytest.approx(0.5)
    assert v.maj_at_k(samples, golds, 6) == pytest.approx(0.0), "câu 1: hoà 3-3, đáp số xuất hiện trước là 1"


def test_maj_at_k_drops_incomplete_block(v):
    samples = [["7", "7", "8", "8", "8"]]
    assert v.maj_at_k(samples, ["7"], 2) == pytest.approx(0.5), "5 lời giải, k = 2: hai khối đủ, lời giải thứ 5 bỏ"
    with pytest.raises(ValueError):
        v.maj_at_k(samples, ["7"], 6)


def test_coverage_at_k(v):
    samples = [["1", "2", "3", "4"], ["9", "9", "9", "9"], ["5", "5", None, "6"]]
    golds = ["3", "8", "5"]
    expected = (v.pass_at_k(4, 1, 2) + 0.0 + v.pass_at_k(4, 2, 2)) / 3
    assert v.coverage_at_k(samples, golds, 2) == pytest.approx(expected)
    assert v.coverage_at_k(samples, golds, 4) == pytest.approx(2 / 3)


def test_vote_beats_single_sample_when_model_is_more_often_right(v):
    rng = random.Random(0)
    samples = [[("42" if rng.random() < 0.45 else str(rng.randint(0, 40))) for _ in range(16)] for _ in range(300)]
    golds = ["42"] * 300
    one, sixteen = v.maj_at_k(samples, golds, 1), v.maj_at_k(samples, golds, 16)
    assert 0.40 < one < 0.50
    assert sixteen > 0.95, "đáp án đúng chiếm 45%, các đáp án sai phân tán: bỏ phiếu gần như luôn đúng"
    assert v.coverage_at_k(samples, golds, 16) >= sixteen
