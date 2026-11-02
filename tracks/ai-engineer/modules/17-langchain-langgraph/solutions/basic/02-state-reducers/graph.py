"""StateGraph tra cứu nhiều vế: state có kiểu và reducer, fan-out bằng Send, cạnh có điều kiện, vòng lặp có ngân sách."""

import operator
from functools import partial
from typing import Annotated, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send


class Evidence(TypedDict):
    uid: str
    score: float
    part: str


def merge_evidence(left: list[Evidence], right: list[Evidence]) -> list[Evidence]:
    best: dict[str, Evidence] = {}
    for ev in [*(left or []), *(right or [])]:
        old = best.get(ev["uid"])
        if old is None or (ev["score"], old["part"]) > (old["score"], ev["part"]):
            best[ev["uid"]] = ev
    return sorted(best.values(), key=lambda ev: (-ev["score"], ev["uid"]))


class ResearchState(TypedDict):
    question: str
    parts: list[str]
    evidence: Annotated[list[Evidence], merge_evidence]
    attempts: Annotated[int, operator.add]
    answer: str


class PartState(TypedDict):
    part: str


def route_parts(state: dict) -> list[Send] | str:
    searched = {ev["part"] for ev in state.get("evidence") or []}
    todo = [p for p in state["parts"] if p not in searched]
    return [Send("retrieve", {"part": p}) for p in todo] or "answer"


def weak_parts(state: dict, min_score: float) -> list[str]:
    strong = {ev["part"] for ev in state.get("evidence") or [] if ev["score"] >= min_score}
    return [p for p in state["parts"] if p not in strong]


def should_continue(state: dict, *, min_score: float, max_attempts: int) -> str:
    if not weak_parts(state, min_score) or state.get("attempts", 0) >= max_attempts:
        return "answer"
    return "rewrite"


def build_graph(split_fn: Callable[[str], list[str]], search_fn: Callable[[str], list[tuple[str, float]]],
                rewrite_fn: Callable[[str], str], answer_fn: Callable[[str, list[Evidence]], str], *,
                min_score: float = 0.5, max_attempts: int = 2):
    def split(state: ResearchState) -> dict:
        return {"parts": split_fn(state["question"]) or [state["question"]]}

    def retrieve(state: PartState) -> dict:
        return {"evidence": [{"uid": uid, "score": score, "part": state["part"]}
                             for uid, score in search_fn(state["part"])]}

    def judge(state: ResearchState) -> dict:
        return {"attempts": 1}

    def rewrite(state: ResearchState) -> dict:
        weak = set(weak_parts(state, min_score))
        return {"parts": [rewrite_fn(p) if p in weak else p for p in state["parts"]]}

    def answer(state: ResearchState) -> dict:
        return {"answer": answer_fn(state["question"], state.get("evidence") or [])}

    g = StateGraph(ResearchState)
    g.add_node("split", split)
    g.add_node("retrieve", retrieve)
    g.add_node("judge", judge)
    g.add_node("rewrite", rewrite)
    g.add_node("answer", answer)
    g.add_edge(START, "split")
    g.add_conditional_edges("split", route_parts, ["retrieve", "answer"])
    g.add_edge("retrieve", "judge")
    g.add_conditional_edges("judge", partial(should_continue, min_score=min_score, max_attempts=max_attempts),
                            ["answer", "rewrite"])
    g.add_conditional_edges("rewrite", route_parts, ["retrieve", "answer"])
    g.add_edge("answer", END)
    return g.compile()
