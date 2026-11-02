import threading
import time

import pytest
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def m():
    return ex.module("lcel.py")


class ScriptedChat(GenericFakeChatModel):
    """Fake chat model của LangChain có bind_tools; mỗi lần gọi lấy phần tử kế tiếp của kịch bản.

    Phần tử là AIMessage (trả về) hoặc Exception (ném ra). Ghi lại messages của mọi lần gọi và số lời gọi chạy
    đồng thời lớn nhất.
    """

    _script: list = PrivateAttr(default_factory=list)
    _lock: object = PrivateAttr(default_factory=threading.Lock)
    _delay: float = PrivateAttr(default=0.0)
    _by_question: object = PrivateAttr(default=None)
    seen: list = []
    active: int = 0
    peak: int = 0

    def __init__(self, script, delay=0.0, by_question=None):
        super().__init__(messages=iter([]))
        self._script = list(script)
        self._delay = delay
        self._by_question = by_question
        self.seen = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        with self._lock:
            self.seen.append(messages)
            self.active += 1
            self.peak = max(self.peak, self.active)
            if self._by_question is not None:
                item = self._by_question(messages[-1].content)
            else:
                assert self._script, "ScriptedChat hết kịch bản"
                item = self._script.pop(0)
        try:
            if self._delay:
                time.sleep(self._delay)
            if isinstance(item, Exception):
                raise item
            return ChatResult(generations=[ChatGeneration(message=item)])
        finally:
            with self._lock:
                self.active -= 1


def analysis_msg(parts, topic="giao thông", missing=()):
    return AIMessage(content="", tool_calls=[{"name": "QuestionAnalysis", "id": "c1",
                                              "args": {"topic": topic, "parts": list(parts), "missing": list(missing)}}])


Q = "Vượt đèn đỏ bị phạt bao nhiêu? Có bị tước bằng lái không?"
PARTS = ["Vượt đèn đỏ bị phạt bao nhiêu?", "Vượt đèn đỏ có bị tước bằng lái không?"]


# ---------- build_analyzer ----------


def test_analyzer_returns_model_and_uses_prompt(m):
    llm = ScriptedChat([analysis_msg(PARTS, missing=["loại phương tiện"])])
    out = m.build_analyzer(llm).invoke({"question": Q})
    assert isinstance(out, m.QuestionAnalysis)
    assert out.parts == PARTS and out.missing == ["loại phương tiện"] and out.topic == "giao thông"
    sent = llm.seen[0]
    assert [x.type for x in sent] == ["system", "human"], "prompt phải là system rồi câu hỏi"
    assert sent[0].content == m.SYSTEM and sent[1].content == Q


def test_analyzer_retries_transient_only(m):
    llm = ScriptedChat([ConnectionError("mất kết nối"), TimeoutError("chậm"), analysis_msg(PARTS)])
    assert m.build_analyzer(llm, attempts=3).invoke({"question": Q}).parts == PARTS
    assert len(llm.seen) == 3

    llm = ScriptedChat([ConnectionError("1"), ConnectionError("2"), analysis_msg(PARTS)])
    with pytest.raises(ConnectionError):
        m.build_analyzer(llm, attempts=2).invoke({"question": Q})
    assert len(llm.seen) == 2, "attempts là tổng số lần thử"

    llm = ScriptedChat([AIMessage(content="", tool_calls=[{"name": "QuestionAnalysis", "id": "c", "args": {"parts": 3}}]),
                        analysis_msg(PARTS)])
    with pytest.raises(Exception):
        m.build_analyzer(llm).invoke({"question": Q})
    assert len(llm.seen) == 1, "output sai schema không phải lỗi tạm thời: gọi lại với cùng input, temperature 0 cho cùng kết quả"


def test_analyzer_rejects_plain_text(m):
    llm = ScriptedChat([AIMessage(content="Mức phạt từ 4 đến 6 triệu đồng.")])
    with pytest.raises(OutputParserException):
        m.build_analyzer(llm).invoke({"question": Q})


# ---------- naive_analysis, with_backup ----------


def test_naive_analysis(m):
    a = m.naive_analysis("  Lương tối thiểu vùng 1?  Làm thêm giờ tối đa bao nhiêu;; ")
    assert a.parts == ["Lương tối thiểu vùng 1", "Làm thêm giờ tối đa bao nhiêu"]
    assert a.topic == "khác" and a.missing == []
    assert m.naive_analysis("Thủ tục ly hôn").parts == ["Thủ tục ly hôn"]


@pytest.mark.parametrize("bad", [
    AIMessage(content="Tôi nghĩ phạt 5 triệu."),
    AIMessage(content="", tool_calls=[{"name": "QuestionAnalysis", "id": "c", "args": {"topic": "thuế", "parts": []}}]),
    AIMessage(content="", tool_calls=[{"name": "Khac", "id": "c", "args": {}}]),
])
def test_backup_on_bad_output(m, bad):
    llm = ScriptedChat([bad])
    out = m.with_backup(m.build_analyzer(llm)).invoke({"question": "Phạt nồng độ cồn? Giữ xe mấy ngày?"})
    assert out.parts == ["Phạt nồng độ cồn", "Giữ xe mấy ngày"] and out.topic == "khác"
    assert len(llm.seen) == 1


def test_backup_not_used_when_primary_ok(m):
    llm = ScriptedChat([analysis_msg(PARTS)])
    out = m.with_backup(m.build_analyzer(llm)).invoke({"question": Q})
    assert out.parts == PARTS and out.topic == "giao thông"


def test_backup_after_retries_exhausted(m):
    llm = ScriptedChat([ConnectionError("a"), ConnectionError("b")])
    out = m.with_backup(m.build_analyzer(llm, attempts=2)).invoke({"question": Q})
    assert out.topic == "khác" and len(out.parts) == 2 and len(llm.seen) == 2


# ---------- build_pipeline ----------


class Search:
    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()

    def __call__(self, query: str) -> list[str]:
        with self.lock:
            self.calls.append(query)
        return [f"doc:{query[:12]}", "doc:chung"]


def test_pipeline_assigns_analysis_and_evidence(m):
    llm = ScriptedChat([analysis_msg(PARTS)])
    search = Search()
    out = m.build_pipeline(m.build_analyzer(llm), search).invoke({"question": Q, "user": "u1"})
    assert out["question"] == Q and out["user"] == "u1", "giữ nguyên mọi khoá đầu vào"
    assert isinstance(out["analysis"], m.QuestionAnalysis)
    assert list(out["evidence"]) == PARTS, "evidence theo đúng thứ tự parts"
    assert out["evidence"][PARTS[1]] == [f"doc:{PARTS[1][:12]}", "doc:chung"]
    assert sorted(search.calls) == sorted(PARTS), "mỗi phần tra đúng một lần"


def test_pipeline_empty_parts_uses_question(m):
    llm = ScriptedChat([analysis_msg([])])
    search = Search()
    out = m.build_pipeline(m.build_analyzer(llm), search).invoke({"question": "Thủ tục ly hôn"})
    assert list(out["evidence"]) == ["Thủ tục ly hôn"] and search.calls == ["Thủ tục ly hôn"]


def test_pipeline_searches_parts_concurrently(m):
    llm = ScriptedChat([analysis_msg(["a1", "a2", "a3", "a4"])])
    gate = threading.Barrier(4, timeout=5)

    def search(q):
        gate.wait()
        return [q]

    out = m.build_pipeline(m.build_analyzer(llm), search).invoke({"question": "x"})
    assert out["evidence"] == {"a1": ["a1"], "a2": ["a2"], "a3": ["a3"], "a4": ["a4"]}


# ---------- analyze_many, CallCounter ----------


def test_analyze_many_isolates_errors_and_limits_concurrency(m):
    def reply(question):
        if "lỗi" in question:
            return ConnectionError("server bận")
        return analysis_msg([question])

    llm = ScriptedChat([], delay=0.05, by_question=reply)
    chain = m.build_analyzer(llm, attempts=1)
    questions = [f"câu {i}" for i in range(7)] + ["câu lỗi"]
    results, errors = m.analyze_many(chain, questions, max_concurrency=3)
    assert len(results) == 8 and results[7] is None
    assert [r.parts for r in results[:7]] == [[f"câu {i}"] for i in range(7)], "giữ thứ tự đầu vào"
    assert list(errors) == [7] and "ConnectionError" in errors[7] and "server bận" in errors[7]
    assert 2 <= llm.peak <= 3, f"chạy song song nhưng không quá max_concurrency (đỉnh {llm.peak})"


def test_analyze_many_with_retry_keeps_results_aligned(m):
    seen = {}

    def reply(question):
        seen[question] = seen.get(question, 0) + 1
        if question == "câu lỗi" or (question == "câu chập chờn" and seen[question] == 1):
            return ConnectionError(f"bận: {question}")
        return analysis_msg([question])

    for attempts in (1, 2):
        seen.clear()
        llm = ScriptedChat([], by_question=reply)
        questions = ["câu 0", "câu chập chờn", "câu lỗi", "câu 3"]
        results, errors = m.analyze_many(m.build_analyzer(llm, attempts=attempts), questions, max_concurrency=2)
        assert list(errors) == ([1, 2] if attempts == 1 else [2]), f"attempts={attempts}: lỗi đúng vị trí"
        assert results[2] is None and "câu lỗi" in errors[2], f"attempts={attempts}: câu lỗi không mượn kết quả câu khác"
        assert results[0].parts == ["câu 0"] and results[3].parts == ["câu 3"]
        if attempts == 2:
            assert results[1].parts == ["câu chập chờn"]


def test_call_counter_counts_retries_and_errors(m):
    llm = ScriptedChat([ConnectionError("x"), analysis_msg(PARTS), analysis_msg(["b"])])
    counter = m.CallCounter()
    chain = m.build_analyzer(llm)
    chain.invoke({"question": Q}, config={"callbacks": [counter]})
    assert (counter.calls, counter.errors) == (2, 1)
    chain.invoke({"question": "b"}, config={"callbacks": [counter]})
    assert (counter.calls, counter.errors) == (3, 1)
