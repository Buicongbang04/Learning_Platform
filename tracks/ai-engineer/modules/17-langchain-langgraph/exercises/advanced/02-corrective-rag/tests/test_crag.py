import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def crag():
    return ex.module("crag.py")


@pytest.mark.parametrize("relevant, rewrites, max_rewrites, expected", [
    (["A"], 0, 1, "answer"), (["A"], 5, 1, "answer"), ([], 0, 1, "rewrite"), ([], 1, 1, "refuse"),
    ([], 0, 0, "refuse"), ([], 1, 2, "rewrite")])
def test_decide_next(crag, relevant, rewrites, max_rewrites, expected):
    assert crag.decide_next(relevant, rewrites, max_rewrites) == expected


ROUNDS = [
    {"uids": ["g1", "a", "b"], "relevant": ["g1", "a"], "gold": {"g1"}},
    {"uids": ["c", "g2", "d"], "relevant": [], "gold": {"g2"}},
    {"uids": ["e", "f", "h"], "relevant": ["e"], "gold": {"g3"}},
    {"uids": ["g4", "g5", "x"], "relevant": ["g5"], "gold": {"g4", "g5"}},
]


def test_grader_agreement(crag):
    out = crag.grader_agreement(ROUNDS)
    assert out["judged"] == 12 and out["marked"] == 4
    assert out["precision"] == pytest.approx(2 / 4)
    assert out["recall"] == pytest.approx(2 / 4), "chỉ tính điều đúng có mặt trong các nguồn được chấm"
    assert out["gold_kept_rate"] == pytest.approx(2 / 3), "câu không có điều đúng trong nguồn không tính"


def test_grader_agreement_empty(crag):
    out = crag.grader_agreement([{"uids": ["a"], "relevant": [], "gold": {"z"}}])
    assert out == {"precision": None, "recall": None, "judged": 1, "marked": 0, "gold_kept_rate": None}
