"""Short-term memory bằng checkpointer: thread, cửa sổ message, SQLite, dòng thời gian, rẽ nhánh và xoá thread."""

import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph

SYSTEM = "Bạn là trợ lý pháp luật. Trả lời ngắn gọn bằng tiếng Việt, dựa vào những gì người dùng đã kể."


def build_chat(llm, checkpointer, *, max_messages: int = 6):
    def chat(state: MessagesState) -> dict:
        window = trim_messages(state["messages"], strategy="last", token_counter=len, max_tokens=max_messages,
                               start_on="human")
        return {"messages": [llm.invoke([SystemMessage(SYSTEM), *window])]}

    g = StateGraph(MessagesState)
    g.add_node("chat", chat)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=checkpointer)


def open_saver(path: str | Path) -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def turn(app, thread_id: str, text: str) -> str:
    out = app.invoke({"messages": [HumanMessage(text)]}, _config(thread_id))
    return out["messages"][-1].content


def timeline(app, thread_id: str) -> list[dict]:
    snap = app.get_state(_config(thread_id))
    if not snap.config["configurable"].get("checkpoint_id"):
        return []
    chain = []
    while snap is not None:
        chain.append({"checkpoint_id": snap.config["configurable"]["checkpoint_id"],
                      "step": snap.metadata["step"], "messages": len(snap.values.get("messages", [])),
                      "next": tuple(snap.next)})
        snap = app.get_state(snap.parent_config) if snap.parent_config else None
    return chain[::-1]


def fork(app, thread_id: str, checkpoint_id: str, text: str) -> str:
    config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}
    out = app.invoke({"messages": [HumanMessage(text)]}, config)
    return out["messages"][-1].content


def forget(checkpointer, thread_id: str) -> None:
    checkpointer.delete_thread(thread_id)
