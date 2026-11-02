"""Short-term memory bằng checkpointer: thread, cửa sổ message, SQLite, dòng thời gian, rẽ nhánh và xoá thread."""

import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph

SYSTEM = "Bạn là trợ lý pháp luật. Trả lời ngắn gọn bằng tiếng Việt, dựa vào những gì người dùng đã kể."


def build_chat(llm, checkpointer, *, max_messages: int = 6):
    """Đồ thị một node "chat" trên MessagesState, compile với checkpointer.

    Mỗi lượt gửi cho llm: SystemMessage(SYSTEM) rồi tối đa `max_messages` message CUỐI của state, cửa sổ phải bắt
    đầu bằng một message người dùng. State vẫn giữ toàn bộ lịch sử; node trả {"messages": [câu trả lời]}.
    """
    # TODO
    raise NotImplementedError


def open_saver(path: str | Path) -> SqliteSaver:
    """SqliteSaver trên tệp `path`, dùng được từ thread khác thread đã mở nó."""
    # TODO
    raise NotImplementedError


def turn(app, thread_id: str, text: str) -> str:
    """Gửi một message người dùng vào thread, trả nội dung câu trả lời."""
    # TODO
    raise NotImplementedError


def timeline(app, thread_id: str) -> list[dict]:
    """Các checkpoint của NHÁNH HIỆN TẠI (từ checkpoint đầu tiên tới checkpoint mới nhất), theo thời gian.

    Mỗi phần tử: {"checkpoint_id", "step" (metadata), "messages" (số message trong state), "next" (tuple tên node)}.
    Thread chưa có gì thì [].
    """
    # TODO
    raise NotImplementedError


def fork(app, thread_id: str, checkpoint_id: str, text: str) -> str:
    """Đi tiếp từ checkpoint `checkpoint_id` (không phải từ checkpoint mới nhất) với message người dùng `text`,
    trả nội dung câu trả lời. Nhánh cũ phải còn nguyên trong checkpointer."""
    # TODO
    raise NotImplementedError


def forget(checkpointer, thread_id: str) -> None:
    """Xoá mọi checkpoint của một thread (người dùng yêu cầu xoá dữ liệu)."""
    # TODO
    raise NotImplementedError
