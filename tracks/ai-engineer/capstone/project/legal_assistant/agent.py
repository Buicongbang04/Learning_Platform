"""M06: các mảnh thuần (không gọi LLM) của agent LangGraph: state, reducer, tách câu hỏi, định tuyến.

Đồ thị dựng trong notebook/script của bạn theo module 17; giữ logic quyết định ở đây để test được bằng fixture.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from .chunking import Passage

Hit = tuple[Passage, float]


def merge_hits(old: list[Hit] | None, new: list[Hit] | None) -> list[Hit]:
    """Reducer của trường `hits`: gộp hai danh sách, mỗi `(uid, label)` giữ một lần với điểm cao nhất, xếp giảm dần
    theo điểm (bằng điểm thì theo `uid`, rồi `label`). `None` coi như rỗng.
    """
    raise NotImplementedError("M06: merge_hits")


class AgentState(TypedDict, total=False):
    question: str
    sub_questions: list[str]
    hits: Annotated[list[Hit], merge_hits]
    missing: str | None
    steps: int
    answer: str


def parse_sub_questions(raw: str, question: str, max_parts: int = 3) -> list[str]:
    """Đọc output JSON `{"sub_questions": [...]}` của bước tách câu hỏi.

    Bỏ phần tử không phải chuỗi hoặc rỗng, `strip`, bỏ trùng, giữ thứ tự, tối đa `max_parts`. JSON hỏng, sai cấu
    trúc hoặc không còn phần tử nào: `[question]` (tra cứu cả câu, không crash).
    """
    raise NotImplementedError("M06: parse_sub_questions")


def next_step(state: AgentState, min_score: float, max_steps: int) -> Literal["clarify", "retrieve", "answer", "refuse"]:
    """Cạnh có điều kiện sau mỗi bước, theo thứ tự ưu tiên:

    1. `missing` khác rỗng: `"clarify"` (hỏi lại người dùng).
    2. Còn vế chưa tra (`len(sub_questions) > steps`) và `steps < max_steps`: `"retrieve"`.
    3. Không có hit, hoặc điểm cao nhất `< min_score`: `"refuse"`.
    4. Còn lại: `"answer"`.
    """
    raise NotImplementedError("M06: next_step")
