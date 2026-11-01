"""Cầu nối MCP -> agent: đổi tool MCP sang spec OpenAI, kết quả sang Observation, client đồng bộ dùng như registry."""

import json
from dataclasses import dataclass

from anyio.from_thread import start_blocking_portal

from mcp import Client
from mcp.shared.exceptions import MCPError


@dataclass
class Observation:
    ok: bool
    content: str


def to_openai_tool(tool) -> dict:
    """mcp.types.Tool -> {"type": "function", "function": {"name", "description", "parameters"}}.

    parameters là tool.input_schema bỏ khoá "title" ở mức ngoài cùng (giữ nguyên phần bên trong), luôn có "type" và
    "properties"; description None thành "".
    """
    # TODO
    raise NotImplementedError


def to_observation(result) -> Observation:
    """mcp.types.CallToolResult -> Observation.

    - is_error: Observation(False, "ERROR: " + các TextContent nối bằng "\n").
    - Có structured_content: dạng {"result": x} (server bọc giá trị không phải object) thì lấy x; rồi
      json.dumps(..., ensure_ascii=False).
    - Không có: nối các TextContent; nếu chuỗi đó là JSON hợp lệ thì dump lại gọn (ensure_ascii=False), không thì giữ.
    """
    # TODO
    raise NotImplementedError


class MCPToolbox:
    """Client MCP đồng bộ có cùng giao diện registry với bài Basic 01/02: specs(), call(name, args).

    with MCPToolbox(server) as tb: ...   # server: MCPServer (in-process) hoặc StdioServerParameters (tiến trình con)

    SDK `mcp` là async. Dùng anyio.from_thread.start_blocking_portal() để chạy event loop ở một thread riêng, rồi
    portal.wrap_async_context_manager(Client(server)) để mở/đóng client, portal.call(async_fn, *args) để gọi.
    """

    def __init__(self, server):
        self.server = server

    def __enter__(self):
        """Mở portal, mở Client, gọi list_tools MỘT lần và giữ spec OpenAI của các tool. Lỗi giữa chừng: đóng portal."""
        # TODO
        raise NotImplementedError

    def __exit__(self, *exc):
        """Đóng client rồi đóng portal (kể cả khi đóng client lỗi)."""
        # TODO
        raise NotImplementedError

    def specs(self) -> list[dict]:
        # TODO
        raise NotImplementedError

    def call(self, name: str, arguments) -> Observation:
        """Gọi tool qua MCP. arguments là dict hoặc chuỗi JSON; không phải object -> Observation(False, "ERROR: ...")
        không gọi server. MCPError -> Observation(False, "ERROR: ..."). Không bao giờ ném lỗi khác của tool."""
        # TODO
        raise NotImplementedError

    def read_resource(self, uri: str) -> str:
        """Nội dung text của resource (các phần nối bằng "\n"). Resource không có: để MCPError lan ra."""
        # TODO
        raise NotImplementedError
