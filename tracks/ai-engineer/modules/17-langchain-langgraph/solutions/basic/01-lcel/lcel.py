"""LCEL: chuỗi phân tích câu hỏi pháp luật có structured output, retry, fallback, nhánh song song, batch và callback."""

import re
from typing import Callable, Literal

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from pydantic import BaseModel, Field


class QuestionAnalysis(BaseModel):
    """Phân tích một câu hỏi pháp luật trước khi tra cứu."""

    topic: Literal["giao thông", "đất đai", "lao động", "hôn nhân", "khác"] = Field(
        description="lĩnh vực pháp luật chính của câu hỏi")
    parts: list[str] = Field(description="các câu hỏi con độc lập, mỗi câu tra cứu được riêng")
    missing: list[str] = Field(default_factory=list,
                               description="thông tin người hỏi chưa cung cấp mà câu trả lời phụ thuộc vào")


SYSTEM = """Bạn phân tích câu hỏi pháp luật tiếng Việt trước khi tra cứu, KHÔNG trả lời câu hỏi.
- topic: lĩnh vực chính.
- parts: tách câu hỏi thành các câu hỏi con độc lập, giữ nguyên ý và từ ngữ của người hỏi; câu chỉ hỏi một ý thì parts có đúng một phần tử là chính câu đó.
- missing: thông tin còn thiếu mà mức phạt hay quyền lợi phụ thuộc vào (ví dụ loại phương tiện); không thiếu gì thì để trống."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", "{question}")])

TRANSIENT = (ConnectionError, TimeoutError)


def _require(result):
    if result is None:
        raise OutputParserException("model không trả structured output (không gọi tool)")
    return result


def build_analyzer(llm, *, attempts: int = 3) -> Runnable:
    chain = PROMPT | llm.with_structured_output(QuestionAnalysis) | RunnableLambda(_require)
    return chain.with_retry(retry_if_exception_type=TRANSIENT, stop_after_attempt=attempts,
                            wait_exponential_jitter=False)


_SPLIT = re.compile(r"[?;]+")


def naive_analysis(question: str) -> QuestionAnalysis:
    parts = [p.strip() for p in _SPLIT.split(question) if p.strip()]
    return QuestionAnalysis(topic="khác", parts=parts or [question.strip()], missing=[])


def with_backup(analyzer: Runnable) -> Runnable:
    backup = RunnableLambda(lambda inputs: naive_analysis(inputs["question"]))
    return analyzer.with_fallbacks([backup])


def build_pipeline(analyzer: Runnable, search: Callable[[str], list[str]]) -> Runnable:
    searcher = RunnableLambda(search)

    def evidence(inputs: dict) -> dict[str, list[str]]:
        parts = inputs["analysis"].parts or [inputs["question"]]
        return dict(zip(parts, searcher.batch(parts)))

    return RunnablePassthrough.assign(analysis=analyzer) | RunnablePassthrough.assign(evidence=evidence)


def analyze_many(chain: Runnable, questions: list[str], *, max_concurrency: int = 4
                 ) -> tuple[list, dict[int, str]]:
    def safe(inputs: dict, config):
        try:
            return chain.invoke(inputs, config)
        except Exception as exc:
            return exc

    outputs = RunnableLambda(safe).batch([{"question": q} for q in questions],
                                         config={"max_concurrency": max_concurrency})
    errors = {i: f"{type(o).__name__}: {o}" for i, o in enumerate(outputs) if isinstance(o, Exception)}
    return [None if isinstance(o, Exception) else o for o in outputs], errors


class CallCounter(BaseCallbackHandler):
    def __init__(self):
        self.calls = 0
        self.errors = 0

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.calls += 1

    def on_llm_error(self, error, **kwargs):
        self.errors += 1
