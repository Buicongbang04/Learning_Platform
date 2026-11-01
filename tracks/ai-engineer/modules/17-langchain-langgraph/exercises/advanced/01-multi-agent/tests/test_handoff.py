import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import PrivateAttr

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def h():
    return ex.module("handoff.py")


class ScriptedChat(GenericFakeChatModel):
    """Fake chat model của LangChain có bind_tools; trả lần lượt các AIMessage kịch bản."""

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
        assert self._script, "ScriptedChat hết kịch bản"
        return ChatResult(generations=[ChatGeneration(message=self._script.pop(0))])


class SwarmState(MessagesState):
    active_agent: str


def agent_graph(name, llm, tools):
    model = llm.bind_tools(tools)

    def call(state):
        return {"messages": [model.invoke(state["messages"])]}

    g = StateGraph(SwarmState)
    g.add_node("model", call)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "model")
    g.add_conditional_edges("model", tools_condition, ["tools", END])
    g.add_edge("tools", "model")
    return g.compile(name=name)


@tool
def get_price(book: str) -> int:
    """Giá một cuốn sách."""
    return 110000


def swarm(h, llm_a, llm_b):
    to_b = h.make_handoff_tool("legal", "Chuyển cho chuyên viên pháp luật khi câu hỏi là về luật.")
    to_a = h.make_handoff_tool("bookstore", "Chuyển cho nhân viên nhà sách khi câu hỏi là về sách, đơn hàng.")
    g = StateGraph(SwarmState)
    g.add_node("bookstore", agent_graph("bookstore", llm_a, [get_price, to_b]), destinations=("legal",))
    g.add_node("legal", agent_graph("legal", llm_b, [to_a]), destinations=("bookstore",))
    g.add_conditional_edges(START, lambda s: s.get("active_agent") or "bookstore", ["bookstore", "legal"])
    return g.compile(checkpointer=InMemorySaver())


def test_handoff_tool_schema(h):
    t = h.make_handoff_tool("legal", "Chuyển cho chuyên viên pháp luật.")
    assert t.name == "transfer_to_legal" and t.description == "Chuyển cho chuyên viên pháp luật."
    schema = t.tool_call_schema.model_json_schema()
    assert schema.get("properties", {}) == {}, "model không phải (và không được) điền state hay tool_call_id"


def test_handoff_moves_control_and_keeps_history(h):
    llm_a = ScriptedChat([AIMessage(content="", tool_calls=[{"name": "transfer_to_legal", "args": {}, "id": "h1"}])])
    llm_b = ScriptedChat([AIMessage(content="Theo Điều 328, phạt cọc gấp đôi là đúng.")])
    app = swarm(h, llm_a, llm_b)
    cfg = {"configurable": {"thread_id": "t"}}
    out = app.invoke({"messages": [HumanMessage("Phạt cọc gấp đôi có đúng luật không?")]}, cfg)
    assert out["active_agent"] == "legal"
    kinds = [(type(m).__name__, getattr(m, "tool_call_id", None)) for m in out["messages"]]
    assert kinds == [("HumanMessage", None), ("AIMessage", None), ("ToolMessage", "h1"), ("AIMessage", None)]
    assert out["messages"][2].content == "Đã chuyển cho legal." and out["messages"][2].name == "transfer_to_legal"
    seen_b = llm_b.seen[0]
    assert isinstance(seen_b[-1], ToolMessage) and seen_b[0].content.startswith("Phạt cọc"), \
        "agent nhận việc thấy toàn bộ lịch sử, kể cả lời gọi handoff đã được trả lời"


def test_next_turn_starts_at_active_agent(h):
    llm_a = ScriptedChat([AIMessage(content="", tool_calls=[{"name": "transfer_to_legal", "args": {}, "id": "h1"}])])
    llm_b = ScriptedChat([AIMessage(content="Đúng."), AIMessage(content="", tool_calls=[
        {"name": "transfer_to_bookstore", "args": {}, "id": "h2"}])])
    llm_a._script.append(AIMessage(content="Mắt biếc giá 110.000 đồng."))
    app = swarm(h, llm_a, llm_b)
    cfg = {"configurable": {"thread_id": "t"}}
    app.invoke({"messages": [HumanMessage("Phạt cọc gấp đôi?")]}, cfg)
    out = app.invoke({"messages": [HumanMessage("Còn sách Mắt biếc giá bao nhiêu?")]}, cfg)
    assert len(llm_b.seen) == 2, "lượt hai bắt đầu ở agent đang giữ quyền (legal)"
    assert out["active_agent"] == "bookstore" and out["messages"][-1].content == "Mắt biếc giá 110.000 đồng."
    assert len(llm_a.seen) == 2
