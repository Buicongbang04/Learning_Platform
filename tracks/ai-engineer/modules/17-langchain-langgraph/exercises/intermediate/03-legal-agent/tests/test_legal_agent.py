import threading

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Send
from pydantic import PrivateAttr

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def la():
    return ex.notebook("legal_agent.ipynb")


class RuleChat(GenericFakeChatModel):
    """Fake chat model của LangChain có bind_tools; câu trả lời do hàm `rule(messages)` quyết định."""

    _rule: object = PrivateAttr(default=None)
    _lock: object = PrivateAttr(default_factory=threading.Lock)
    seen: list = []
    methods: list = []

    def __init__(self, rule):
        super().__init__(messages=iter([]))
        self._rule = rule
        self.seen = []

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, *, method=None, **kwargs):
        self.methods = [*getattr(self, "methods", []), method]
        return super().with_structured_output(schema, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        with self._lock:
            self.seen.append(list(messages))
        item = self._rule(messages)
        if isinstance(item, Exception):
            raise item
        return ChatResult(generations=[ChatGeneration(message=item)])


def plan_msg(parts, missing=(), traffic_fine=None, vehicle=None):
    args = {"parts": list(parts), "traffic_fine": bool(missing) if traffic_fine is None else traffic_fine,
            "vehicle": vehicle or ("không nói" if missing else "xe máy")}
    return AIMessage(content="", tool_calls=[{"name": "Plan", "id": "p", "args": args}])


class Corpus:
    DOCS = {"100/2019/nđ-cp+5": ("Điều 5. Ô tô", "Phạt ô tô vượt đèn đỏ 4-6 triệu."),
            "100/2019/nđ-cp+6": ("Điều 6. Xe máy", "Phạt xe máy vượt đèn đỏ 800 nghìn - 1 triệu."),
            "91/2015/qh13+328": ("Điều 328. Đặt cọc", "Bên nhận cọc vi phạm phải trả gấp đôi."),
            "41/2019/qh14+89": ("Điều 89. Án treo", "Rút ngắn thời gian thử thách.")}

    def __init__(self):
        self.queries = []
        self.lock = threading.Lock()

    def search(self, query, k):
        with self.lock:
            self.queries.append((query, k))
        q = query.lower()
        if "xe máy" in q:
            hits = [("100/2019/nđ-cp+6", 0.8), ("100/2019/nđ-cp+5", 0.7)]
        elif "ô tô" in q:
            hits = [("100/2019/nđ-cp+5", 0.8), ("100/2019/nđ-cp+6", 0.7)]
        elif "cọc" in q:
            hits = [("91/2015/qh13+328", 0.9), ("41/2019/qh14+89", 0.3)]
        elif "án treo" in q:
            hits = [("41/2019/qh14+89", 0.85), ("91/2015/qh13+328", 0.2)]
        else:
            hits = [("100/2019/nđ-cp+5", 0.6), ("100/2019/nđ-cp+6", 0.6)]
        return hits[:k]

    def lookup(self, uid):
        return self.DOCS[uid]


def is_plan(messages, la):
    return messages[0].content == la.PLAN_SYSTEM


# ---------- hàm nhỏ ----------


def test_ask_text_and_search_query(la):
    assert la.ask_text(["loại phương tiện"]) == "Để trả lời chính xác, bạn cho biết thêm: loại phương tiện?"
    assert la.ask_text(["loại xe", "thời điểm"]).endswith("loại xe; thời điểm?")
    assert la.search_query("Vượt đèn đỏ phạt bao nhiêu? ", "xe máy") == \
        "Vượt đèn đỏ phạt bao nhiêu đối với người điều khiển xe máy?"
    assert la.search_query("Mức phạt khi lạng lách", " ô tô ") == "Mức phạt khi lạng lách đối với người điều khiển ô tô?"
    assert la.search_query("Xe máy vượt đèn đỏ phạt bao nhiêu?", "xe máy") == "Xe máy vượt đèn đỏ phạt bao nhiêu?"
    assert la.search_query("Phạt cọc?", "  ") == "Phạt cọc?"


def test_select_sources_per_part(la):
    ev = [{"uid": "A", "score": 0.9, "part": "p1"}, {"uid": "B", "score": 0.8, "part": "p2"},
          {"uid": "C", "score": 0.7, "part": "p1"}, {"uid": "D", "score": 0.6, "part": "p1"},
          {"uid": "E", "score": 0.5, "part": "p2"}]
    assert la.select_sources(ev, ["p1", "p2"], 2) == ["A", "C", "B", "E"]
    assert la.select_sources(ev, ["p2", "p1"], 1) == ["B", "A"]
    assert la.select_sources(ev, ["p3"], 2) == []
    dup = [{"uid": "A", "score": 0.9, "part": "p1"}, {"uid": "A", "score": 0.8, "part": "p2"},
           {"uid": "F", "score": 0.4, "part": "p2"}]
    assert la.select_sources(dup, ["p1", "p2"], 1) == ["A", "F"], "uid đã chọn cho vế trước không chiếm chỗ của vế sau"


def test_parse_citations_and_messages(la):
    assert la.parse_citations("Theo [2] và [1], [2]; xem [7].", 3) == [2, 1]
    msgs = la.build_answer_messages("Phạt cọc?", [("91/2015/qh13+328", "Điều 328. Đặt cọc", "x" * 2000)])
    assert msgs[0].content == la.ANSWER_SYSTEM
    body = msgs[1].content
    assert body.startswith("[1] 91/2015/qh13, Điều 328. Đặt cọc\n") and body.endswith("Câu hỏi: Phạt cọc?")
    assert "x" * la.SOURCE_CHARS in body and "x" * (la.SOURCE_CHARS + 1) not in body


# ---------- node ----------


def test_planner_sends_question_and_falls_back(la):
    llm = RuleChat(lambda m: plan_msg([" Phạt cọc gấp đôi có đúng không? ", "Án treo?"]))
    out = la.make_planner(llm)({"question": "Phạt cọc gấp đôi có đúng không? Án treo?", "clarification": ""})
    assert out == {"parts": ["Phạt cọc gấp đôi có đúng không?", "Án treo?"], "missing": [], "llm_calls": 1}
    sent = llm.seen[0]
    assert [m.type for m in sent] == ["system", "human"]
    assert sent[0].content == la.PLAN_SYSTEM and sent[1].content == "Phạt cọc gấp đôi có đúng không? Án treo?"

    assert llm.methods == ["json_schema"]

    for bad in (AIMessage(content="Phạt 1 triệu."), ConnectionError("mất mạng"), plan_msg(["  ", ""], vehicle="ô tô"),
                AIMessage(content="", tool_calls=[{"name": "Plan", "id": "p", "args": {"parts": ["a"], "vehicle": "tàu"}}])):
        out = la.make_planner(RuleChat(lambda m, b=bad: b))({"question": "Q?", "clarification": ""})
        assert out["parts"] == ["Q?"] and out["missing"] == [] and out["llm_calls"] == 1


@pytest.mark.parametrize("fine, vehicle, missing", [
    (True, "không nói", True), (True, "xe máy", False), (True, "loại xe khác", False), (False, "không nói", False)])
def test_planner_missing_decided_by_code(la, fine, vehicle, missing):
    llm = RuleChat(lambda m: plan_msg(["Q?"], traffic_fine=fine, vehicle=vehicle))
    out = la.make_planner(llm)({"question": "Q?", "clarification": ""})
    assert out["missing"] == ([la.VEHICLE_SLOT] if missing else [])


def test_route_after_plan(la):
    assert la.route_after_plan({"parts": ["a"], "missing": ["loại xe"], "asked": 0}) == "clarify"
    sends = la.route_after_plan({"parts": ["a", "b"], "missing": ["loại xe"], "asked": 1, "clarification": "ô tô"})
    assert [(s.node, s.arg) for s in sends] == [("retrieve", {"part": "a", "clarification": "ô tô"}),
                                               ("retrieve", {"part": "b", "clarification": "ô tô"})]
    assert all(isinstance(s, Send) for s in la.route_after_plan({"parts": ["a"], "missing": []}))


def test_retriever_tags_part_and_uses_clarification(la):
    corpus = Corpus()
    out = la.make_retriever(corpus.search, 2)({"part": "Vượt đèn đỏ phạt bao nhiêu?", "clarification": "xe máy"})
    assert corpus.queries == [("Vượt đèn đỏ phạt bao nhiêu đối với người điều khiển xe máy?", 2)]
    assert out == {"evidence": [{"uid": "100/2019/nđ-cp+6", "score": 0.8, "part": "Vượt đèn đỏ phạt bao nhiêu?"},
                                {"uid": "100/2019/nđ-cp+5", "score": 0.7, "part": "Vượt đèn đỏ phạt bao nhiêu?"}]}


def test_answerer_maps_citations_and_refuses_without_sources(la):
    corpus = Corpus()
    llm = RuleChat(lambda m: AIMessage(content="Phải trả gấp đôi [2]."))
    state = {"question": "Phạt cọc?", "clarification": "", "parts": ["Phạt cọc?"],
             "evidence": [{"uid": "91/2015/qh13+328", "score": 0.9, "part": "Phạt cọc?"},
                          {"uid": "41/2019/qh14+89", "score": 0.3, "part": "Phạt cọc?"}]}
    out = la.make_answerer(llm, corpus.lookup, 2)(state)
    assert out["sources"] == ["91/2015/qh13+328", "41/2019/qh14+89"]
    assert out["citations"] == ["41/2019/qh14+89"] and out["llm_calls"] == 1
    assert "[2] 41/2019/qh14, Điều 89. Án treo" in llm.seen[0][1].content

    empty = la.make_answerer(llm, corpus.lookup, 2)({**state, "evidence": []})
    assert empty["answer"] == la.REFUSAL and empty["citations"] == [] and len(llm.seen) == 1


# ---------- cả đồ thị ----------


def rule_for(la, plans, answer="Theo [1]."):
    def rule(messages):
        if is_plan(messages, la):
            text = messages[1].content
            for key, value in plans.items():
                if key in text:
                    return value(text) if callable(value) else value
            return plan_msg([text])
        return AIMessage(content=answer)
    return rule


def test_two_part_question_retrieves_each_part(la):
    corpus = Corpus()
    q = "Phạt cọc gấp đôi có đúng không, và người hưởng án treo có được rút ngắn thử thách?"
    llm = RuleChat(rule_for(la, {"Phạt cọc": plan_msg(["Phạt cọc gấp đôi có đúng không?",
                                                        "Người hưởng án treo có được rút ngắn thử thách?"])},
                            answer="Đúng [1]; được [2]."))
    app = la.build_legal_agent(llm, corpus.search, corpus.lookup, k=2, per_part=1, checkpointer=InMemorySaver())
    out = la.run_question(app, "t1", q)
    assert sorted(x for x, _ in corpus.queries) == sorted(["Phạt cọc gấp đôi có đúng không?",
                                                          "Người hưởng án treo có được rút ngắn thử thách?"])
    assert out["sources"] == ["91/2015/qh13+328", "41/2019/qh14+89"]
    assert out["citations"] == ["91/2015/qh13+328", "41/2019/qh14+89"]
    assert out["asked"] == [] and out["llm_calls"] == 2 and out["answer"] == "Đúng [1]; được [2]."


def test_ask_back_then_answer_with_right_article(la):
    corpus = Corpus()
    plans = {"Vượt đèn đỏ": plan_msg(["Vượt đèn đỏ phạt bao nhiêu?"], ["x"])}
    llm = RuleChat(rule_for(la, plans))
    app = la.build_legal_agent(llm, corpus.search, corpus.lookup, k=2, per_part=1, checkpointer=InMemorySaver())

    waiting = la.run_question(app, "t2", "Vượt đèn đỏ phạt bao nhiêu?")
    assert waiting["answer"] is None and waiting["asked"] == [la.ask_text([la.VEHICLE_SLOT])]
    assert corpus.queries == [], "chưa biết loại xe thì chưa tra"

    replies = []
    out = la.run_question(app, "t3", "Vượt đèn đỏ phạt bao nhiêu?", reply_fn=lambda q: replies.append(q) or "xe máy")
    assert replies == [la.ask_text([la.VEHICLE_SLOT])]
    assert out["asked"] == replies and out["sources"] == ["100/2019/nđ-cp+6"]
    assert out["citations"] == ["100/2019/nđ-cp+6"] and out["llm_calls"] == 2, "không lập kế hoạch lại sau khi hỏi"
    assert corpus.queries == [("Vượt đèn đỏ phạt bao nhiêu đối với người điều khiển xe máy?", 2)]
    assert "(xe máy)" in llm.seen[-1][1].content, "câu hỏi gửi cho bước trả lời mang theo thông tin bổ sung"


def test_asks_at_most_once(la):
    corpus = Corpus()
    llm = RuleChat(rule_for(la, {"Vượt": plan_msg(["Vượt đèn đỏ phạt bao nhiêu?"], ["x"])}))
    app = la.build_legal_agent(llm, corpus.search, corpus.lookup, k=2, per_part=1, checkpointer=InMemorySaver())
    out = la.run_question(app, "t4", "Vượt đèn đỏ phạt bao nhiêu?", reply_fn=lambda q: "ô tô")
    assert len(out["asked"]) == 1 and out["answer"] == "Theo [1]."
    assert corpus.queries == [("Vượt đèn đỏ phạt bao nhiêu đối với người điều khiển ô tô?", 2)]
    assert out["sources"] == ["100/2019/nđ-cp+5"]


def test_threads_are_independent(la):
    corpus = Corpus()
    llm = RuleChat(rule_for(la, {"Vượt": plan_msg(["Vượt đèn đỏ phạt bao nhiêu?"], ["x"])}))
    app = la.build_legal_agent(llm, corpus.search, corpus.lookup, k=2, per_part=1, checkpointer=InMemorySaver())
    assert la.run_question(app, "a", "Vượt đèn đỏ phạt bao nhiêu?")["answer"] is None
    other = la.run_question(app, "b", "Phạt cọc gấp đôi?")
    assert other["asked"] == [] and other["sources"] == ["91/2015/qh13+328"]
    pending = app.get_state({"configurable": {"thread_id": "a"}})
    assert [i.value["type"] for i in pending.interrupts] == ["ask"], "thread a vẫn đang chờ trả lời"
