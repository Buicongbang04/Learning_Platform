"""Human-in-the-loop với interrupt: hỏi lại người dùng khi thiếu thông tin, duyệt / sửa / từ chối tool có tác dụng phụ."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt

ASK_TOOL = "ask_user"


def route_after_agent(state: MessagesState) -> str:
    """"review" nếu message cuối là AIMessage có tool call; ngược lại END."""
    # TODO
    raise NotImplementedError


def make_review(sensitive: set[str]):
    """Trả node `review(state) -> Command` xét các tool call của AIMessage cuối, theo thứ tự:

    - ASK_TOOL: dừng hỏi người dùng, interrupt({"type": "ask", "question": <args["question"]>}); giá trị resume
      thành ToolMessage trả lời đúng tool call đó.
    - tool trong `sensitive`: interrupt({"type": "approve", "tool": <tên>, "args": <args>}); giá trị resume là
      {"action": "approve"} | {"action": "edit", "args": {...}} | {"action": "reject", "reason": "..."}.
      approve: giữ nguyên; edit: thay args của chính tool call đó; reject: ToolMessage status "error", nội dung bắt
      đầu bằng "REJECTED: " kèm lý do, tool KHÔNG được chạy.
    - tool khác: giữ nguyên.

    Cập nhật state: AIMessage (cùng id, tool call đã sửa nếu có) và các ToolMessage vừa tạo. Còn tool call chưa có trả
    lời thì goto "tools", ngược lại goto "agent". Node này KHÔNG chạy tool nào.
    """
    # TODO
    raise NotImplementedError


def make_tool_runner(tools: list[BaseTool]):
    """Trả node chạy các tool call của AIMessage cuối CHƯA có ToolMessage trả lời, mỗi cái một ToolMessage.

    Tool ném lỗi (hoặc tên tool không có) thì ToolMessage status "error", nội dung bắt đầu bằng "ERROR".
    """
    # TODO
    raise NotImplementedError


def build_app(llm, tools: list[BaseTool], *, sensitive: set[str], checkpointer):
    """Đồ thị agent -> (route_after_agent) -> review -> tools -> agent, compile với checkpointer."""
    # TODO
    raise NotImplementedError


def start(app, thread_id: str, text: str) -> tuple[str | None, list[dict]]:
    """Gửi message người dùng. Trả (câu trả lời cuối, []) hoặc (None, [giá trị của các interrupt đang chờ])."""
    # TODO
    raise NotImplementedError


def resume(app, thread_id: str, value) -> tuple[str | None, list[dict]]:
    """Trả lời interrupt đang chờ của thread bằng `value`; kết quả như `start`. Không có gì đang chờ: ValueError."""
    # TODO
    raise NotImplementedError
