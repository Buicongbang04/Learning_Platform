"""Handoff giữa các agent (kiểu swarm): một tool trả Command chuyển quyền điều khiển sang agent khác ở đồ thị cha."""

from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command


def make_handoff_tool(agent_name: str, description: str) -> BaseTool:
    """Tool tên `transfer_to_<agent_name>`, mô tả `description`, model gọi KHÔNG cần tham số nào.

    Khi chạy (trong ToolNode của một agent là subgraph), trả Command chuyển sang node `agent_name` của đồ thị CHA,
    cập nhật: "messages" = toàn bộ messages hiện tại của agent + ToolMessage("Đã chuyển cho <agent_name>.") trả lời
    đúng tool call này (name là tên tool), và "active_agent" = agent_name.
    """
    # TODO
    raise NotImplementedError
