import json
import math

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("judge.ipynb")


# ---------- dán từ Basic 02 ----------

def test_pasted_basic_functions(nb):
    assert nb.cohen_kappa([True] * 9 + [False], [True] * 10) == pytest.approx(0.0)
    r = nb.calibration_report([True, False, None, True], [True, True, False, False])
    assert r["n"] == 3 and r["unparsed"] == 1 and r["false_pass"] == pytest.approx(1.0)
    assert nb.resolve_swap("first", "first") == "inconsistent"
    assert nb.pairwise_summary([("first", "second"), ("tie", "tie")])["win_rate_A"] == pytest.approx(0.75)


# ---------- make_items ----------

def test_make_items_follows_rng_recipe(nb):
    gold = ["negative", "neutral", "positive"] * 20
    cands, truth = nb.make_items(gold, seed=0)
    rng = np.random.default_rng(0)
    for g, c, t in zip(gold, cands, truth):
        if rng.random() < 0.5:
            others = [x for x in nb.LABELS if x != g]
            assert (c, t) == (others[int(rng.integers(0, 2))], False)
        else:
            assert (c, t) == (g, True)


def test_make_items_properties(nb):
    gold = list(np.random.default_rng(1).choice(["negative", "neutral", "positive"], size=400))
    cands, truth = nb.make_items(gold, seed=3, flip_rate=0.3)
    assert len(cands) == len(truth) == 400
    assert all((c == g) == t for c, g, t in zip(cands, gold, truth)), "truth đúng khi và chỉ khi ứng viên trùng gold"
    assert 0.24 <= 1 - np.mean(truth) <= 0.36
    assert nb.make_items(gold, seed=3, flip_rate=0.3) == (cands, truth)
    assert all(nb.make_items(gold, flip_rate=0.0)[1]) and not any(nb.make_items(gold, flip_rate=1.0)[1])


# ---------- prompt và parse ----------

def test_judge_messages(nb):
    msgs = nb.judge_messages("thầy dạy rất hay .", "negative")
    assert msgs[0] == {"role": "system", "content": nb.JUDGE_SYSTEM}
    assert msgs[1] == {"role": "user", "content": "Phản hồi: thầy dạy rất hay .\nNhãn hệ thống gán: negative"}


@pytest.mark.parametrize("reply, expected", [
    ("yes", True), (" Yes.\n", True), ("no", False), ("NO", False),
    ("yes, nhãn đúng", None), ("có", None), ("", None), ("no no", None),
])
def test_parse_yes_no(nb, reply, expected):
    assert nb.parse_yes_no(reply) is expected


def test_p_yes(nb):
    top = [{"token": "yes", "logprob": math.log(0.6)}, {"token": " Yes", "logprob": math.log(0.1)},
           {"token": "no", "logprob": math.log(0.2)}, {"token": "maybe", "logprob": math.log(0.05)}]
    assert nb.p_yes(top) == pytest.approx(0.7 / 0.9)
    assert nb.p_yes([{"token": "no", "logprob": -0.01}]) == pytest.approx(0.0)
    assert nb.p_yes([{"token": "ok", "logprob": -0.1}]) is None
    assert nb.p_yes([]) is None and nb.p_yes(None) is None


# ---------- calibration ----------

def test_ece_hand_example(nb):
    probs = [0.95, 0.95, 0.95, 0.95, 0.15, 0.15, 1.0, None]  # 1.0 thuộc khoảng cuối
    truth = [True, True, True, False, False, True, False, True]
    expected = (5 / 7) * abs(0.96 - 0.6) + (2 / 7) * abs(0.15 - 0.5)
    assert nb.expected_calibration_error(probs, truth) == pytest.approx(expected)
    assert nb.expected_calibration_error([0.25, 0.25, 0.75, 0.75], [False, True, True, True], n_bins=2) \
        == pytest.approx(0.5 * 0.25 + 0.5 * 0.25)


def test_ece_perfectly_calibrated_is_small(nb):
    rng = np.random.default_rng(0)
    p = rng.uniform(size=20_000)
    y = rng.uniform(size=20_000) < p
    assert nb.expected_calibration_error(list(p), list(y)) < 0.02
    assert nb.expected_calibration_error(list(np.full(1000, 0.99)), [True] * 500 + [False] * 500) \
        == pytest.approx(0.49)
    with pytest.raises(ValueError):
        nb.expected_calibration_error([None], [True])


def test_pick_threshold(nb):
    scores = [0.9, 0.8, 0.3, 0.2, 0.6, None]
    truth = [True, True, False, False, False, True]
    assert nb.pick_threshold(scores, truth) == pytest.approx(0.8)
    assert nb.pick_threshold([0.1, 0.2], [False, False]) > 0.2, "không cho qua câu nào khi mọi câu đều sai"
    assert nb.pick_threshold([0.4, 0.4, 0.7], [True, False, True]) == pytest.approx(0.4), "bằng nhau lấy ngưỡng nhỏ nhất"
    with pytest.raises(ValueError):
        nb.pick_threshold([None], [True])


# ---------- pairwise ----------

def test_pair_messages(nb):
    msgs = nb.pair_messages("Hỏi?", "đoạn A", "đoạn B")
    assert msgs[0] == {"role": "system", "content": nb.PAIR_SYSTEM}
    assert msgs[1]["content"] == "Câu hỏi: Hỏi?\n\nĐoạn 1:\nđoạn A\n\nĐoạn 2:\nđoạn B"


@pytest.mark.parametrize("reply, expected", [
    ('{"choice": "1"}', "first"), (' {"choice": "2"} ', "second"), ('{"choice": "tie"}', "tie"),
    ('{"choice": 1}', None), ('{"choice": "3"}', None), ('{"pick": "1"}', None), ("1", None),
    ('["1"]', None), ('{"choice": ["1"]}', None), ("không chắc", None), ('{"choice": "1"', None),
])
def test_parse_choice(nb, reply, expected):
    assert nb.parse_choice(reply) == expected


def test_judge_pair_swaps_order(nb):
    calls = []

    def first_lover(messages):
        calls.append(messages[1]["content"])
        return json.dumps({"choice": "1"})

    assert nb.judge_pair(first_lover, "Hỏi?", "ĐÚNG", "SAI") == ("first", "first")
    assert len(calls) == 2
    assert calls[0].index("ĐÚNG") < calls[0].index("SAI") and calls[1].index("SAI") < calls[1].index("ĐÚNG")

    def content_judge(messages):
        text = messages[1]["content"]
        return json.dumps({"choice": "1" if text.index("ĐÚNG") < text.index("SAI") else "2"})

    v = nb.judge_pair(content_judge, "Hỏi?", "ĐÚNG", "SAI")
    assert v == ("first", "second") and nb.resolve_swap(*v) == "A"
