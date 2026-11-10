import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def rg():
    return ex.notebook("react_graph.ipynb")


@pytest.fixture(scope="module")
def bookstore(rg):
    import importlib.util

    path = ex.path("bookstore.py")
    spec = importlib.util.spec_from_file_location("bookstore_i01", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ScriptedChat(GenericFakeChatModel):
    """Fake chat model của LangChain có bind_tools; trả lần lượt AIMessage kịch bản (hết thì lặp phần tử cuối)."""

    _script: list = PrivateAttr(default_factory=list)
    seen: list = []
    bound: list = []

    def __init__(self, script):
        super().__init__(messages=iter([]))
        self._script = list(script)
        self.seen = []
        self.bound = []

    def bind_tools(self, tools, **kwargs):
        self.bound.append([getattr(t, "name", t) for t in tools])
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        item = self._script.pop(0) if len(self._script) > 1 else self._script[0]
        return ChatResult(generations=[ChatGeneration(message=item)])


def call(name, args, cid):
    return {"name": name, "args": args, "id": cid, "type": "tool_call"}


# ---------- make_tools, format_tool_error ----------


def test_make_tools_schema(rg, bookstore):
    tools = rg.make_tools(bookstore.TOOLS)
    assert [t.name for t in tools] == ["search_books", "get_book", "get_order", "calculator", "exchange_rate"]
    assert tools[1].description.startswith("Thông tin đầy đủ của một cuốn sách theo mã")
    assert "Args" not in tools[1].description
    schema = tools[4].tool_call_schema.model_json_schema()
    assert schema["properties"]["currency"]["enum"] == ["USD", "EUR", "JPY"]
    assert schema["properties"]["currency"]["description"] == "mã ngoại tệ"
    assert tools[3].invoke({"expression": "3 * 55000"}) == 165000
    with pytest.raises(ValueError):
        tools[1].invoke({"book_id": "XX"})


def test_format_tool_error(rg):
    assert rg.format_tool_error(ValueError("không có sách mã 'XX'")) == "ERROR: ValueError: không có sách mã 'XX'"
    assert rg.format_tool_error(ZeroDivisionError("division by zero")).startswith("ERROR: ZeroDivisionError: ")


# ---------- build_agent, run_task ----------


def test_agent_tool_then_answer(rg, bookstore):
    llm = ScriptedChat([AIMessage(content="", tool_calls=[call("get_book", {"book_id": "B05"}, "c1")]),
                        AIMessage(content="Mắt biếc giá 110.000 đồng.")])
    app = rg.build_agent(llm, rg.make_tools(bookstore.TOOLS), max_steps=8)
    out = rg.run_task(app, "Mắt biếc giá bao nhiêu?")
    assert out["answer"] == "Mắt biếc giá 110.000 đồng." and out["stopped"] == "answer" and out["llm_calls"] == 2
    assert llm.bound and llm.bound[0][0] == "search_books"
    second = llm.seen[1]
    assert second[0].type == "system" and second[0].content == rg.NATIVE_SYSTEM
    assert isinstance(second[-1], ToolMessage) and '"price": 110000' in second[-1].content
    assert [type(m).__name__ for m in out["messages"]] == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"], \
        "system prompt không nằm trong state"


def test_agent_tool_error_is_observation(rg, bookstore):
    llm = ScriptedChat([AIMessage(content="", tool_calls=[call("get_book", {"book_id": "DTNT"}, "c1")]),
                        AIMessage(content="", tool_calls=[call("search_books", {"query": "Đắc nhân tâm"}, "c2")]),
                        AIMessage(content="86.000 đồng")])
    out = rg.run_task(rg.build_agent(llm, rg.make_tools(bookstore.TOOLS)), "Giá Đắc nhân tâm?")
    err = out["messages"][2]
    assert isinstance(err, ToolMessage) and err.status == "error"
    assert err.content.startswith("ERROR: ValueError: ") and "search_books" in err.content
    assert out["answer"] == "86.000 đồng" and out["llm_calls"] == 3


def test_agent_budget(rg, bookstore):
    loop = AIMessage(content="", tool_calls=[call("calculator", {"expression": "1+1"}, "c")])
    llm = ScriptedChat([loop])
    out = rg.run_task(rg.build_agent(llm, rg.make_tools(bookstore.TOOLS), max_steps=3), "x")
    assert out["stopped"] == "max_steps" and out["answer"] is None
    assert out["llm_calls"] == 3 and len(llm.seen) == 3
    assert sum(isinstance(m, ToolMessage) for m in out["messages"]) == 2, "lượt cuối hết ngân sách thì không chạy tool"

    out1 = rg.run_task(rg.build_agent(ScriptedChat([loop]), rg.make_tools(bookstore.TOOLS), max_steps=1), "x")
    assert out1["llm_calls"] == 1 and out1["stopped"] == "max_steps"


def test_agent_answer_on_last_allowed_call(rg, bookstore):
    llm = ScriptedChat([AIMessage(content="", tool_calls=[call("calculator", {"expression": "2*3"}, "c1")]),
                        AIMessage(content="6")])
    out = rg.run_task(rg.build_agent(llm, rg.make_tools(bookstore.TOOLS), max_steps=2), "2*3?")
    assert out["stopped"] == "answer" and out["answer"] == "6"


def test_agent_parallel_tool_calls(rg, bookstore):
    llm = ScriptedChat([AIMessage(content="", tool_calls=[call("get_book", {"book_id": "B13"}, "a"),
                                                         call("get_book", {"book_id": "B20"}, "b")]),
                        AIMessage(content="xong")])
    out = rg.run_task(rg.build_agent(llm, rg.make_tools(bookstore.TOOLS)), "x")
    tool_msgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert sorted(m.tool_call_id for m in tool_msgs) == ["a", "b"] and out["llm_calls"] == 2


def test_run_task_passes_recursion_limit(rg, bookstore):
    from langgraph.errors import GraphRecursionError

    loop = AIMessage(content="", tool_calls=[call("calculator", {"expression": "1+1"}, "c")])
    app = rg.build_agent(ScriptedChat([loop]), rg.make_tools(bookstore.TOOLS), max_steps=50)
    with pytest.raises(GraphRecursionError):
        rg.run_task(app, "x", recursion_limit=5)


# ---------- to_steps ----------


def test_to_steps(rg):
    messages = [HumanMessage("q"),
                AIMessage(content="", tool_calls=[call("get_book", {"book_id": "X"}, "1"), call("calculator", {"expression": "1"}, "2")]),
                ToolMessage(content="1", tool_call_id="2", status="success"),
                ToolMessage(content="ERROR: ValueError: x", tool_call_id="1", status="error"),
                AIMessage(content="", tool_calls=[call("calculator", {"expression": "2"}, "3")]),
                ToolMessage(content=[{"type": "text", "text": "2"}], tool_call_id="3"),
                AIMessage(content="", tool_calls=[call("calculator", {"expression": "9"}, "4")]),
                AIMessage(content="", tool_calls=[call("get_order", {"order_id": "DH9"}, "5")]),
                ToolMessage(content="không có đơn này", tool_call_id="5", status="error"),
                AIMessage(content="xong")]
    steps = rg.to_steps(messages)
    assert [(s["index"], s["kind"], s["tool"]) for s in steps] == [
        (0, "action", "get_book"), (0, "action", "calculator"), (1, "action", "calculator"),
        (2, "action", "calculator"), (3, "action", "get_order"), (4, "final", None)]
    assert steps[0]["observation"] == "ERROR: ValueError: x" and steps[0]["ok"] is False
    assert steps[1]["observation"] == "1" and steps[1]["ok"] is True and steps[1]["args"] == {"expression": "1"}
    assert isinstance(steps[2]["observation"], str) and steps[2]["ok"] is True
    assert steps[3]["observation"] is None and steps[3]["ok"] is None
    assert steps[4]["ok"] is False, "ok đọc từ status của ToolMessage, không đoán từ nội dung"
    assert steps[5] == {"index": 4, "kind": "final", "tool": None, "args": None, "observation": None, "ok": None}
