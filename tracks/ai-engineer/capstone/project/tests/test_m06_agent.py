"""M06: reducer, tách câu hỏi, định tuyến; reducer chạy đúng trong một StateGraph thật."""

import json

from langgraph.graph import END, START, StateGraph


def _p(la, uid, label=""):
    return la("chunking").Passage(uid, label, f"{uid} {label}")


def test_merge_hits(la):
    agent = la("agent")
    a1, a2, b = _p(la, "A+1", "khoản 1"), _p(la, "A+1", "khoản 2"), _p(la, "B+1")
    out = agent.merge_hits([(a1, 0.5), (b, 0.7)], [(a1, 0.9), (a2, 0.7)])
    assert [(p.uid, p.label, s) for p, s in out] == [
        ("A+1", "khoản 1", 0.9), ("A+1", "khoản 2", 0.7), ("B+1", "", 0.7),
    ]
    assert agent.merge_hits(None, [(b, 0.1)]) == [(b, 0.1)]
    assert agent.merge_hits([(b, 0.3)], None) == [(b, 0.3)]


def test_parse_sub_questions(la):
    agent = la("agent")
    q = "Câu gốc?"
    raw = json.dumps({"sub_questions": [" Vế 1? ", "Vế 2?", "Vế 1?", "", 3, "Vế 3?", "Vế 4?"]})
    assert agent.parse_sub_questions(raw, q) == ["Vế 1?", "Vế 2?", "Vế 3?"]
    assert agent.parse_sub_questions(raw, q, max_parts=1) == ["Vế 1?"]
    for bad in ["không phải json", json.dumps({"sub_questions": []}), json.dumps({"x": 1}),
                json.dumps({"sub_questions": "Vế 1?"}), json.dumps(["Vế 1?"])]:
        assert agent.parse_sub_questions(bad, q) == [q], bad


def test_next_step(la):
    agent = la("agent")
    hit = (_p(la, "A+1"), 0.8)
    low = (_p(la, "A+2"), 0.3)
    assert agent.next_step({"missing": "loại xe", "hits": [hit]}, 0.5, 3) == "clarify"
    assert agent.next_step({"sub_questions": ["a", "b"], "steps": 1, "hits": [hit]}, 0.5, 3) == "retrieve"
    assert agent.next_step({"sub_questions": ["a", "b", "c"], "steps": 2, "hits": [hit]}, 0.5, 2) == "answer"
    assert agent.next_step({"sub_questions": ["a"], "steps": 1, "hits": []}, 0.5, 3) == "refuse"
    assert agent.next_step({"sub_questions": ["a"], "steps": 1, "hits": [low]}, 0.5, 3) == "refuse"
    assert agent.next_step({"sub_questions": ["a"], "steps": 1, "hits": [low, hit], "missing": None}, 0.5, 3) == "answer"
    assert agent.next_step({"question": "x"}, 0.5, 3) == "refuse"


def test_state_reducer_in_langgraph(la):
    agent = la("agent")
    hit_a, hit_b = (_p(la, "A+1"), 0.4), (_p(la, "B+1"), 0.9)

    def first(state):
        return {"hits": [hit_a], "steps": 1}

    def second(state):
        return {"hits": [hit_b, (_p(la, "A+1"), 0.6)], "steps": 2}

    graph = StateGraph(agent.AgentState)
    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.add_edge(START, "first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)
    out = graph.compile().invoke({"question": "q"})
    assert [(p.uid, s) for p, s in out["hits"]] == [("B+1", 0.9), ("A+1", 0.6)]
    assert out["steps"] == 2
