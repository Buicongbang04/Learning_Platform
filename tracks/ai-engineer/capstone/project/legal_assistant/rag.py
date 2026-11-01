"""M03: một lượt RAG có cổng từ chối hai lớp (module 13, mục 5 "Từ chối khi thiếu căn cứ")."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .chunking import Passage


@dataclass
class RagAnswer:
    text: str
    citations: list[str]
    refused: bool
    gated: bool
    passages: list[Passage] = field(default_factory=list)
    seconds: float = 0.0


def answer(question: str, retrieve: Callable[[str], list[tuple[Passage, float]]], llm, min_score: float) -> RagAnswer:
    """`retrieve(question)` trả `[(passage, điểm)]` đã xếp hạng; `llm` có `.chat(messages)` như `llmkit`.

    - Không có hit hoặc điểm cao nhất `< min_score`: trả `REFUSAL`, `gated=True`, **không gọi LLM**, `passages=[]`.
    - Ngược lại gọi `llm.chat` đúng một lần với `build_messages(question, passages)`; `refused` theo `is_refusal`;
      `citations` là `cited_uids` (rỗng nếu từ chối); `passages` là các passage đã đưa vào prompt.
    - `seconds`: thời gian cả lượt (đo bằng `time.perf_counter`).
    """
    raise NotImplementedError("M03: answer")
