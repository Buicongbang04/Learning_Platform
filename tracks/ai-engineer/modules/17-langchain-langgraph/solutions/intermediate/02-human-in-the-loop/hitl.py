"""Human-in-the-loop với interrupt: hỏi lại người dùng khi thiếu thông tin, duyệt / sửa / từ chối tool có tác dụng phụ."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt

ASK_TOOL = "ask_user"


def route_after_agent(state: MessagesState) -> str:
    last = state["messages"][-1]
    return "review" if isinstance(last, AIMessage) and last.tool_calls else END


def make_review(sensitive: set[str]):
    def review(state: MessagesState) -> Command:
        ai = state["messages"][-1]
        calls, replies = [], []
        for call in ai.tool_calls:
            if call["name"] == ASK_TOOL:
                answer = interrupt({"type": "ask", "question": call["args"].get("question", "")})
                replies.append(ToolMessage(content=str(answer), tool_call_id=call["id"], name=ASK_TOOL))
                calls.append(call)
            elif call["name"] in sensitive:
                decision = interrupt({"type": "approve", "tool": call["name"], "args": call["args"]})
                action = decision.get("action")
                if action == "approve":
                    calls.append(call)
                elif action == "edit":
                    calls.append({**call, "args": decision["args"]})
                else:
                    calls.append(call)
                    replies.append(ToolMessage(content=f"REJECTED: {decision.get('reason', 'người dùng từ chối')}",
                                               tool_call_id=call["id"], name=call["name"], status="error"))
            else:
                calls.append(call)
        answered = {m.tool_call_id for m in replies}
        updated = AIMessage(content=ai.content, tool_calls=calls, id=ai.id)
        runnable = [c for c in calls if c["id"] not in answered]
        return Command(goto="tools" if runnable else "agent", update={"messages": [updated, *replies]})

    return review


def make_tool_runner(tools: list[BaseTool]):
    by_name = {t.name: t for t in tools}

    def run_tools(state: MessagesState) -> dict:
        messages = state["messages"]
        ai = next(m for m in reversed(messages) if isinstance(m, AIMessage))
        answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
        out = []
        for call in ai.tool_calls:
            if call["id"] in answered:
                continue
            tool = by_name.get(call["name"])
            try:
                if tool is None:
                    raise ValueError(f"không có tool {call['name']!r}")
                content, status = str(tool.invoke(call["args"])), "success"
            except Exception as exc:
                content, status = f"ERROR: {type(exc).__name__}: {exc}", "error"
            out.append(ToolMessage(content=content, tool_call_id=call["id"], name=call["name"], status=status))
        return {"messages": out}

    return run_tools


def build_app(llm, tools: list[BaseTool], *, sensitive: set[str], checkpointer):
    model = llm.bind_tools(tools)

    def agent(state: MessagesState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("review", make_review(sensitive), destinations=("tools", "agent"))
    g.add_node("tools", make_tool_runner(tools))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route_after_agent, ["review", END])
    g.add_edge("tools", "agent")
    return g.compile(checkpointer=checkpointer)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _result(app, thread_id: str) -> tuple[str | None, list[dict]]:
    snap = app.get_state(_config(thread_id))
    waiting = [i.value for i in snap.interrupts]
    if waiting:
        return None, waiting
    return snap.values["messages"][-1].content, []


def start(app, thread_id: str, text: str) -> tuple[str | None, list[dict]]:
    app.invoke({"messages": [HumanMessage(text)]}, _config(thread_id))
    return _result(app, thread_id)


def resume(app, thread_id: str, value) -> tuple[str | None, list[dict]]:
    if not app.get_state(_config(thread_id)).interrupts:
        raise ValueError(f"thread {thread_id!r} không có gì đang chờ")
    app.invoke(Command(resume=value), _config(thread_id))
    return _result(app, thread_id)
