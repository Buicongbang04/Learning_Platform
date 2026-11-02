import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import PrivateAttr

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def h():
    return ex.module("hitl.py")


class ScriptedChat(GenericFakeChatModel):
    """Fake chat model của LangChain có bind_tools: trả lần lượt các AIMessage kịch bản, ghi lại messages mỗi lần gọi."""

    _script: list = PrivateAttr(default_factory=list)
    seen: list = []

    def __init__(self, script):
        super().__init__(messages=iter([]))
        self._script = list(script)
        self.seen = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        assert self._script, "ScriptedChat hết kịch bản: agent gọi model nhiều hơn dự kiến"
        return ChatResult(generations=[ChatGeneration(message=self._script.pop(0))])


def call(name, args, cid):
    return {"name": name, "args": args, "id": cid, "type": "tool_call"}


def ai_calls(*calls, content=""):
    return AIMessage(content=content, tool_calls=list(calls))


class World:
    def __init__(self):
        self.outbox = []
        self.searches = []

        @tool
        def search_law(query: str) -> str:
            """Tìm điều luật liên quan."""
            self.searches.append(query)
            if query == "lỗi":
                raise RuntimeError("chỉ mục đang bận")
            return f"Điều 6 NĐ 100/2019: kết quả cho {query}"

        @tool
        def send_email(to: str, body: str) -> str:
            """Gửi email câu trả lời cho người dùng."""
            self.outbox.append((to, body))
            return f"đã gửi tới {to}"

        @tool
        def ask_user(question: str) -> str:
            """Hỏi lại người dùng khi thiếu thông tin."""
            raise AssertionError("ask_user không bao giờ được thực thi như tool thường")

        self.tools = [search_law, send_email, ask_user]


def build(h, script, world=None):
    world = world or World()
    llm = ScriptedChat(script)
    app = h.build_app(llm, world.tools, sensitive={"send_email"}, checkpointer=InMemorySaver())
    return app, llm, world


def history(app, thread):
    return app.get_state({"configurable": {"thread_id": thread}}).values["messages"]


def assert_protocol(messages):
    """Mỗi tool call có đúng một ToolMessage trả lời, đứng sau AIMessage của nó."""
    for i, m in enumerate(messages):
        if isinstance(m, AIMessage):
            for c in m.tool_calls:
                replies = [x for x in messages[i + 1:] if isinstance(x, ToolMessage) and x.tool_call_id == c["id"]]
                assert len(replies) == 1, f"tool call {c['id']} có {len(replies)} ToolMessage"
    for i, m in enumerate(messages):
        if isinstance(m, ToolMessage):
            owners = [x for x in messages[:i] if isinstance(x, AIMessage) and
                      any(c["id"] == m.tool_call_id for c in x.tool_calls)]
            assert owners, f"ToolMessage {m.tool_call_id} không thuộc tool call nào"
    ids = [m.id for m in messages if isinstance(m, AIMessage)]
    assert len(ids) == len(set(ids)), "một AIMessage xuất hiện hai lần trong state"


def test_route_after_agent(h):
    assert h.route_after_agent({"messages": [AIMessage(content="xong")]}) == "__end__"
    assert h.route_after_agent({"messages": [ai_calls(call("search_law", {"query": "x"}, "1"))]}) == "review"


def test_plain_answer_and_safe_tool(h):
    app, llm, world = build(h, [ai_calls(call("search_law", {"query": "vượt đèn đỏ"}, "c1")), AIMessage(content="Phạt.")])
    assert h.start(app, "t", "Vượt đèn đỏ phạt sao?") == ("Phạt.", [])
    assert world.searches == ["vượt đèn đỏ"] and len(llm.seen) == 2
    assert isinstance(llm.seen[1][-1], ToolMessage) and "Điều 6" in llm.seen[1][-1].content
    assert_protocol(history(app, "t"))


def test_ask_back_interrupts_and_resumes(h):
    app, llm, world = build(h, [ai_calls(call("ask_user", {"question": "Bạn đi xe máy hay ô tô?"}, "a1")),
                                AIMessage(content="Xe máy: phạt 4-6 triệu.")])
    answer, waiting = h.start(app, "t", "Vượt đèn đỏ phạt bao nhiêu?")
    assert answer is None and waiting == [{"type": "ask", "question": "Bạn đi xe máy hay ô tô?"}]
    assert len(llm.seen) == 1
    assert h.resume(app, "t", "xe máy") == ("Xe máy: phạt 4-6 triệu.", [])
    last_seen = llm.seen[1][-1]
    assert isinstance(last_seen, ToolMessage) and last_seen.content == "xe máy" and last_seen.tool_call_id == "a1"
    assert len(llm.seen) == 2, "resume không gọi lại model cho lượt đã có"
    assert_protocol(history(app, "t"))


def test_approve_executes_side_effect_once(h):
    send = call("send_email", {"to": "lan@x.vn", "body": "Mức phạt ..."}, "s1")
    app, llm, world = build(h, [ai_calls(send), AIMessage(content="Đã gửi.")])
    answer, waiting = h.start(app, "t", "Gửi câu trả lời cho tôi qua email lan@x.vn")
    assert answer is None
    assert waiting == [{"type": "approve", "tool": "send_email", "args": {"to": "lan@x.vn", "body": "Mức phạt ..."}}]
    assert world.outbox == [], "chưa duyệt thì chưa được gửi"
    assert h.resume(app, "t", {"action": "approve"}) == ("Đã gửi.", [])
    assert world.outbox == [("lan@x.vn", "Mức phạt ...")]
    assert_protocol(history(app, "t"))


def test_edit_replaces_args_in_place(h):
    send = call("send_email", {"to": "lan@x.vn", "body": "nháp"}, "s1")
    app, llm, world = build(h, [ai_calls(send), AIMessage(content="Đã gửi bản sửa.")])
    h.start(app, "t", "gửi email")
    h.resume(app, "t", {"action": "edit", "args": {"to": "lan@y.vn", "body": "bản cuối"}})
    assert world.outbox == [("lan@y.vn", "bản cuối")]
    msgs = history(app, "t")
    ai = [m for m in msgs if isinstance(m, AIMessage) and m.tool_calls]
    assert len(ai) == 1 and ai[0].tool_calls[0]["args"] == {"to": "lan@y.vn", "body": "bản cuối"}, \
        "state phải ghi đúng tham số đã thực thi, không giữ bản nháp"
    assert_protocol(msgs)


def test_reject_tells_model_and_skips_tool(h):
    send = call("send_email", {"to": "sep@congty.vn", "body": "..."}, "s1")
    app, llm, world = build(h, [ai_calls(send), AIMessage(content="Tôi sẽ không gửi.")])
    h.start(app, "t", "gửi cho sếp tôi")
    assert h.resume(app, "t", {"action": "reject", "reason": "không gửi ra ngoài"}) == ("Tôi sẽ không gửi.", [])
    assert world.outbox == []
    rejected = llm.seen[1][-1]
    assert isinstance(rejected, ToolMessage) and rejected.tool_call_id == "s1"
    assert rejected.content.startswith("REJECTED") and "không gửi ra ngoài" in rejected.content
    assert_protocol(history(app, "t"))


def test_two_interrupts_in_one_turn(h):
    msg = ai_calls(call("search_law", {"query": "nồng độ cồn"}, "q1"),
                   call("ask_user", {"question": "Loại xe?"}, "a1"),
                   call("send_email", {"to": "u@x.vn", "body": "b"}, "s1"))
    app, llm, world = build(h, [msg, AIMessage(content="xong")])
    answer, waiting = h.start(app, "t", "...")
    assert waiting == [{"type": "ask", "question": "Loại xe?"}]
    answer, waiting = h.resume(app, "t", "ô tô")
    assert answer is None and waiting[0]["type"] == "approve" and waiting[0]["tool"] == "send_email"
    assert world.outbox == [] and world.searches == []
    assert h.resume(app, "t", {"action": "approve"}) == ("xong", [])
    assert world.searches == ["nồng độ cồn"] and world.outbox == [("u@x.vn", "b")]
    seen = {m.tool_call_id: m.content for m in llm.seen[1] if isinstance(m, ToolMessage)}
    assert seen["a1"] == "ô tô" and seen["s1"] == "đã gửi tới u@x.vn" and "Điều 6" in seen["q1"]
    assert_protocol(history(app, "t"))


def test_approval_then_question_side_effect_once(h):
    msg = ai_calls(call("send_email", {"to": "u@x.vn", "body": "b"}, "s1"),
                   call("ask_user", {"question": "Gửi thêm bản sao cho ai?"}, "a1"))
    app, llm, world = build(h, [msg, AIMessage(content="xong")])
    assert h.start(app, "t", "...")[1][0]["type"] == "approve"
    answer, waiting = h.resume(app, "t", {"action": "approve"})
    assert waiting == [{"type": "ask", "question": "Gửi thêm bản sao cho ai?"}]
    assert world.outbox == [], "chưa xong lượt duyệt thì chưa gửi"
    assert h.resume(app, "t", "không ai") == ("xong", [])
    assert world.outbox == [("u@x.vn", "b")], "tác dụng phụ chạy đúng một lần dù node duyệt chạy lại khi resume"
    assert_protocol(history(app, "t"))


def test_tool_error_is_observation(h):
    app, llm, world = build(h, [ai_calls(call("search_law", {"query": "lỗi"}, "q1")),
                                ai_calls(call("search_law", {"query": "đèn đỏ"}, "q2")), AIMessage(content="ok")])
    assert h.start(app, "t", "x") == ("ok", [])
    err = llm.seen[1][-1]
    assert isinstance(err, ToolMessage) and err.content.startswith("ERROR") and "bận" in err.content
    assert world.searches == ["lỗi", "đèn đỏ"]


def test_threads_isolated_and_resume_needs_pending(h):
    world = World()
    script = [ai_calls(call("ask_user", {"question": "Loại xe?"}, "a1")), AIMessage(content="B xong"),
              AIMessage(content="A xong")]
    app, llm, _ = build(h, script, world)
    assert h.start(app, "A", "câu A")[1] == [{"type": "ask", "question": "Loại xe?"}]
    assert h.start(app, "B", "câu B") == ("B xong", [])
    with pytest.raises(ValueError):
        h.resume(app, "B", "xe máy")
    assert h.resume(app, "A", "xe máy") == ("A xong", [])
