"""Chuyển request/response giữa ba "phương ngữ" của Chat API: OpenAI Chat Completions, Anthropic Messages, Ollama.

Dạng chuẩn nội bộ của bài là message kiểu OpenAI Chat Completions (`system`, `user`, `assistant` có thể kèm
`tool_calls`, `tool`). Mọi response được đưa về một `Reply` chung để code phía sau không phụ thuộc nhà cung cấp.
Chỉ dùng thư viện chuẩn. Đọc README của bài cho định dạng đầy đủ.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict          # đã parse thành dict, không phải chuỗi JSON


@dataclass
class Reply:
    text: str                                          # "" khi model không viết chữ nào
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"                        # "stop" | "length" | "tool_calls"
    prompt_tokens: int = 0
    completion_tokens: int = 0


def to_anthropic(messages: list[dict], tools: list[dict] | None = None, *, model: str, max_tokens: int = 1024) -> dict:
    """Body cho POST /v1/messages của Anthropic từ hội thoại và tools kiểu OpenAI.

    - Mọi message `system` thành khoá `system` cấp ngoài (nối bằng "\\n\\n"); không có thì bỏ khoá.
    - `user`: giữ chuỗi `content`.
    - `assistant`: content là danh sách khối: khối `text` (nếu content khác rỗng/None), rồi mỗi tool call một khối
      `tool_use` với `id`, `name`, `input` (dict; arguments có thể là chuỗi JSON hoặc dict).
    - `tool`: khối `tool_result` (`tool_use_id`, `content`) trong một message `user`; các message `tool` liên tiếp
      gom vào CÙNG một message `user`.
    - tools: `{"name", "description", "input_schema"}`; không có tools thì bỏ khoá `tools`.
    - ValueError: arguments không phải JSON object, hoặc `tool_call_id` không ứng với tool call nào trước đó.
    Không sửa `messages` đầu vào.
    """
    # TODO
    raise NotImplementedError


def parse_openai(resp: dict) -> Reply:
    """Reply từ response JSON của POST /v1/chat/completions (choice đầu tiên)."""
    # TODO
    raise NotImplementedError


def parse_anthropic(resp: dict) -> Reply:
    """Reply từ response JSON của POST /v1/messages: nối mọi khối text, khối tool_use thành ToolCall,
    stop_reason đổi về finish_reason kiểu OpenAI, usage input_tokens/output_tokens."""
    # TODO
    raise NotImplementedError


def parse_ollama(resp: dict) -> Reply:
    """Reply từ response JSON của POST /api/chat (stream false) của Ollama.

    Tool call của Ollama không có `id` (bản mới có thể có): thiếu thì đặt `call_<thứ tự>`. Ollama báo
    `done_reason` "stop" cả khi model gọi tool, nên finish_reason phải tự suy ra.
    """
    # TODO
    raise NotImplementedError
