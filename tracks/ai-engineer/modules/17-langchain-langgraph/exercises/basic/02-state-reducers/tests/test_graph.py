import operator
import random
import threading
import time
import typing

import pytest
from langgraph.types import Send

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def g():
    return ex.module("graph.py")


def ev(uid, score, part="p"):
    return {"uid": uid, "score": score, "part": part}


# ---------- merge_evidence ----------


def test_merge_union_keeps_best_and_sorts(g):
    left = [ev("A", 0.5, "p1"), ev("B", 0.9, "p1")]
    right = [ev("A", 0.7, "p2"), ev("C", 0.9, "p2")]
    assert g.merge_evidence(left, right) == [ev("B", 0.9, "p1"), ev("C", 0.9, "p2"), ev("A", 0.7, "p2")]


def test_merge_tie_keeps_smaller_part(g):
    assert g.merge_evidence([ev("A", 0.5, "p2")], [ev("A", 0.5, "p1")]) == [ev("A", 0.5, "p1")]
    assert g.merge_evidence([ev("A", 0.5, "p1")], [ev("A", 0.5, "p2")]) == [ev("A", 0.5, "p1")]


def test_merge_does_not_mutate_and_handles_empty(g):
    left = [ev("A", 0.5)]
    right = [ev("A", 0.4)]
    snapshot = ([dict(x) for x in left], [dict(x) for x in right])
    assert g.merge_evidence(left, right) == [ev("A", 0.5)]
    assert (left, right) == snapshot
    assert g.merge_evidence([], []) == []
    assert g.merge_evidence(None, [ev("Z", 0.1)]) == [ev("Z", 0.1)]


def test_merge_is_order_independent(g):
    rng = random.Random(0)
    batches = [[ev(rng.choice("ABCDEFG"), round(rng.random(), 1), f"p{i}") for _ in range(4)] for i in range(5)]
    results = set()
    for _ in range(20):
        rng.shuffle(batches)
        acc = []
        for b in batches:
            acc = g.merge_evidence(acc, b)
        results.add(tuple((x["uid"], x["score"], x["part"]) for x in acc))
    assert len(results) == 1, "kết quả gộp phụ thuộc thứ tự các cập nhật được áp"
    uids = [u for u, _, _ in next(iter(results))]
    assert len(uids) == len(set(uids))


def test_state_declares_reducers(g):
    hints = typing.get_type_hints(g.ResearchState, include_extras=True)
    assert set(hints) >= {"question", "parts", "evidence", "attempts", "answer"}
    assert hints["evidence"].__metadata__[0] is g.merge_evidence
    assert hints["attempts"].__metadata__[0] is operator.add
    assert not hasattr(hints["parts"], "__metadata__"), "parts được ghi đè mỗi lần, không cộng dồn"


# ---------- route_parts, weak_parts, should_continue ----------


def test_route_parts_sends_only_unsearched(g):
    state = {"parts": ["a", "b", "c"], "evidence": [ev("X", 0.2, "b")]}
    sends = g.route_parts(state)
    assert all(isinstance(s, Send) for s in sends)
    assert [(s.node, s.arg) for s in sends] == [("retrieve", {"part": "a"}), ("retrieve", {"part": "c"})]
    assert g.route_parts({"parts": ["a"], "evidence": [ev("X", 0.1, "a")]}) == "answer"
    assert len(g.route_parts({"parts": ["a", "b"]})) == 2


def test_weak_parts(g):
    state = {"parts": ["a", "b", "c"], "evidence": [ev("X", 0.8, "a"), ev("Y", 0.3, "b"), ev("Z", 0.5, "c")]}
    assert g.weak_parts(state, 0.5) == ["b"]
    assert g.weak_parts(state, 0.9) == ["a", "b", "c"]
    assert g.weak_parts({"parts": ["a"], "evidence": []}, 0.0) == ["a"]


def test_should_continue(g):
    weak = {"parts": ["a"], "evidence": [ev("X", 0.2, "a")], "attempts": 1}
    assert g.should_continue(weak, min_score=0.5, max_attempts=2) == "rewrite"
    assert g.should_continue({**weak, "attempts": 2}, min_score=0.5, max_attempts=2) == "answer"
    assert g.should_continue(weak, min_score=0.2, max_attempts=2) == "answer"


# ---------- build_graph ----------


class Env:
    """Hàm thật thay cho LLM và retriever: ghi lại lời gọi, chạy song song có độ trễ ngẫu nhiên."""

    def __init__(self, table, seed=0, rewrite=None):
        self.table = table
        self.rng = random.Random(seed)
        self.lock = threading.Lock()
        self.searches = []
        self.rewrites = []
        self.rewrite_map = rewrite or {}

    def split(self, q):
        return [p.strip() for p in q.split("|") if p.strip()]

    def search(self, part):
        with self.lock:
            self.searches.append(part)
            delay = self.rng.random() * 0.02
        time.sleep(delay)
        return self.table.get(part, [])

    def rewrite(self, part):
        self.rewrites.append(part)
        return self.rewrite_map.get(part, part + " (viết lại)")

    def answer(self, question, evidence):
        return ",".join(e["uid"] for e in evidence)


TABLE = {"phạt": [("A", 0.9), ("B", 0.4)], "tước bằng": [("B", 0.8), ("C", 0.7)], "giữ xe": [("D", 0.3)],
         "giữ xe (viết lại)": [("E", 0.6), ("A", 0.2)]}


def build(g, env, **kw):
    return g.build_graph(env.split, env.search, env.rewrite, env.answer, **kw)


def test_graph_nodes(g):
    nodes = set(build(g, Env(TABLE)).get_graph().nodes)
    assert {"split", "retrieve", "judge", "rewrite", "answer"} <= nodes


def test_parallel_parts_merge_without_conflict(g):
    env = Env(TABLE)
    out = build(g, env, min_score=0.5).invoke({"question": "phạt | tước bằng"})
    assert out["parts"] == ["phạt", "tước bằng"]
    assert sorted(env.searches) == ["phạt", "tước bằng"]
    assert [(e["uid"], e["score"]) for e in out["evidence"]] == [("A", 0.9), ("B", 0.8), ("C", 0.7)]
    assert out["attempts"] == 1 and env.rewrites == []
    assert out["answer"] == "A,B,C"


def test_rewrite_loop_only_researches_weak_part(g):
    env = Env(TABLE)
    out = build(g, env, min_score=0.5, max_attempts=3).invoke({"question": "phạt | giữ xe"})
    assert env.rewrites == ["giữ xe"]
    assert sorted(env.searches) == ["giữ xe", "giữ xe (viết lại)", "phạt"], "chỉ tra lại phần còn yếu"
    assert out["parts"] == ["phạt", "giữ xe (viết lại)"]
    assert out["attempts"] == 2
    assert [e["uid"] for e in out["evidence"]] == ["A", "E", "B", "D"]


def test_loop_stops_at_budget(g):
    env = Env({}, rewrite={})
    out = build(g, env, min_score=0.5, max_attempts=3).invoke({"question": "x"})
    assert out["attempts"] == 3 and len(env.rewrites) == 2 and len(env.searches) == 3
    assert out["answer"] == ""


def test_rewrite_without_change_goes_to_answer(g):
    env = Env({"x": [("A", 0.1)]}, rewrite={"x": "x"})
    out = build(g, env, min_score=0.5, max_attempts=5).invoke({"question": "x"})
    assert env.searches == ["x"] and out["attempts"] == 1 and out["answer"] == "A"


def test_empty_split_uses_question(g):
    env = Env({"Thủ tục ly hôn": [("A", 0.3)]})
    env.split = lambda q: []
    out = build(g, env, min_score=0.0).invoke({"question": "Thủ tục ly hôn"})
    assert out["parts"] == ["Thủ tục ly hôn"] and env.searches == ["Thủ tục ly hôn"]


def test_same_result_whatever_part_order(g):
    """Đổi thứ tự các vế (tức thứ tự Send) không được đổi state cuối, kể cả vế mà evidence bằng điểm được gắn vào."""
    import itertools

    table = {"p1": [("A", 0.6), ("B", 0.6)], "p2": [("B", 0.6), ("C", 0.9)], "p3": [("A", 0.7)]}
    results = set()
    for order in itertools.permutations(["p1", "p2", "p3"]):
        out = build(g, Env(table)).invoke({"question": " | ".join(order)})
        results.add(tuple((e["uid"], e["score"], e["part"]) for e in out["evidence"]))
        assert out["answer"] == "C,A,B"
    assert results == {(("C", 0.9, "p2"), ("A", 0.7, "p3"), ("B", 0.6, "p1"))}, \
        "state cuối phụ thuộc thứ tự các vế trong câu hỏi"
