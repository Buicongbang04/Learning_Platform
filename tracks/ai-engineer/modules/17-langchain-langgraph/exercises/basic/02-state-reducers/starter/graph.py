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
    """Reducer của khoá evidence: hợp hai danh sách theo uid.

    - Trùng uid: giữ bản có score cao hơn; bằng score thì giữ bản có `part` nhỏ hơn (so chuỗi).
    - Kết quả xếp theo score giảm dần, bằng score thì uid tăng dần.
    - `left` có thể là None (khoá chưa có giá trị). Không sửa list đầu vào.
    """
    # TODO
    raise NotImplementedError


class ResearchState(TypedDict):
    # TODO: thêm reducer cho các khoá cần cộng dồn (xem đề bài)
    question: str
    parts: list[str]
    evidence: list[Evidence]
    attempts: int
    answer: str


class PartState(TypedDict):
    part: str


def route_parts(state: dict) -> list[Send] | str:
    """Một Send("retrieve", {"part": p}) cho mỗi phần p trong state["parts"] chưa có evidence nào gắn part == p,
    theo thứ tự parts. Không còn phần nào cần tra thì trả "answer"."""
    # TODO
    raise NotImplementedError


def weak_parts(state: dict, min_score: float) -> list[str]:
    """Các phần (theo thứ tự parts) không có evidence nào gắn với nó đạt score >= min_score."""
    # TODO
    raise NotImplementedError


def should_continue(state: dict, *, min_score: float, max_attempts: int) -> str:
    """"answer" nếu không còn phần yếu hoặc attempts >= max_attempts; ngược lại "rewrite"."""
    # TODO
    raise NotImplementedError


def build_graph(split_fn: Callable[[str], list[str]], search_fn: Callable[[str], list[tuple[str, float]]],
                rewrite_fn: Callable[[str], str], answer_fn: Callable[[str, list[Evidence]], str], *,
                min_score: float = 0.5, max_attempts: int = 2):
    """Biên dịch StateGraph(ResearchState) với 5 node: split, retrieve, judge, rewrite, answer (xem sơ đồ trong đề)."""
    # TODO
    raise NotImplementedError
