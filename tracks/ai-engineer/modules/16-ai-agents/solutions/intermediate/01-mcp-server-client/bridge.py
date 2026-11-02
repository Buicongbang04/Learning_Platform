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
    parameters = {k: v for k, v in tool.input_schema.items() if k != "title"}
    parameters.setdefault("type", "object")
    parameters.setdefault("properties", {})
    return {"type": "function", "function": {"name": tool.name, "description": tool.description or "",
                                             "parameters": parameters}}


def to_observation(result) -> Observation:
    texts = [block.text for block in result.content if getattr(block, "type", None) == "text"]
    if result.is_error:
        return Observation(False, "ERROR: " + ("\n".join(texts) or "tool lỗi, server không gửi thông điệp"))
    data = result.structured_content
    if data is not None:
        if isinstance(data, dict) and set(data) == {"result"}:
            data = data["result"]
        return Observation(True, json.dumps(data, ensure_ascii=False))
    text = "\n".join(texts)
    try:
        return Observation(True, json.dumps(json.loads(text), ensure_ascii=False))
    except ValueError:
        return Observation(True, text)


class MCPToolbox:
    def __init__(self, server):
        self.server = server
        self._portal_cm = None
        self._client_cm = None
        self._client = None
        self._specs: list[dict] = []

    def __enter__(self):
        self._portal_cm = start_blocking_portal()
        portal = self._portal_cm.__enter__()
        self._client_cm = portal.wrap_async_context_manager(Client(self.server))
        try:
            self._client = self._client_cm.__enter__()
            listed = portal.call(self._client.list_tools)
        except BaseException:
            self._portal_cm.__exit__(None, None, None)
            raise
        self._portal = portal
        self._specs = [to_openai_tool(t) for t in listed.tools]
        return self

    def __exit__(self, *exc):
        try:
            self._client_cm.__exit__(*exc)
        finally:
            self._portal_cm.__exit__(*exc)
        return False

    def specs(self) -> list[dict]:
        return list(self._specs)

    def call(self, name: str, arguments) -> Observation:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                arguments = None
        if not isinstance(arguments, dict):
            return Observation(False, f"ERROR: tham số của {name} phải là một JSON object.")
        try:
            result = self._portal.call(self._client.call_tool, name, arguments)
        except MCPError as exc:
            return Observation(False, f"ERROR: {name}: {exc}")
        return to_observation(result)

    def read_resource(self, uri: str) -> str:
        result = self._portal.call(self._client.read_resource, uri)
        return "\n".join(getattr(c, "text", "") for c in result.contents)
