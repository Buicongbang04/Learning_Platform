"""Vòng ReAct tự viết: parse output dạng Thought/Action/Action Input, gọi tool, ngân sách bước, điều kiện dừng, trace."""

import json
import re
import time
from dataclasses import dataclass, field

import llmkit


@dataclass
class Action:
    tool: str
    args: dict
    thought: str = ""


@dataclass
class Final:
    answer: str
    thought: str = ""


class ReActParseError(ValueError):
    pass


@dataclass
class Step:
    index: int
    kind: str
    reply: str
    tool: str | None = None
    args: dict | None = None
    observation: str | None = None
    ok: bool | None = None
    seconds: float = 0.0


@dataclass
class RunResult:
    answer: str | None
    stopped: str
    steps: list[Step] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    tool_errors: int = 0
    format_errors: int = 0
    error: str | None = None


SYSTEM_TEMPLATE = """Bạn là một agent giải quyết yêu cầu của người dùng bằng cách dùng tool. Các tool có sẵn:

{tools}

Mỗi lượt, trả lời đúng MỘT trong hai dạng sau, không viết gì khác:

Thought: <suy nghĩ ngắn: cần làm gì tiếp>
Action: <tên tool>
Action Input: <tham số dạng JSON object>

hoặc, khi đã đủ thông tin:

Thought: <suy nghĩ ngắn>
Final Answer: <câu trả lời cho người dùng, tiếng Việt>

Sau mỗi Action, hệ thống trả về `Observation: <kết quả>`. Không tự viết Observation. Số liệu phải lấy từ Observation,
không tự bịa."""


def render_tools(specs: list[dict]) -> str:
    lines = []
    for spec in specs:
        f = spec["function"]
        lines.append(f"- {f['name']}: {f['description']}\n  Tham số (JSON Schema): "
                     f"{json.dumps(f['parameters'], ensure_ascii=False)}")
    return "\n".join(lines)


def clean_reply(text: str) -> str:
    """Bỏ mọi thứ từ dòng `Observation:` đầu tiên trở đi (model nhỏ hay tự bịa Observation), strip hai đầu."""
    # TODO
    raise NotImplementedError


def parse_react(text: str) -> Action | Final:
    """Đọc một lượt trả lời của model (sau clean_reply).

    - Có dòng `Action: <tool>` đứng trước `Final Answer:` (hoặc không có Final Answer): trả Action. Tên tool bỏ dấu
      ` ' " * bao quanh. Tham số là JSON object đầu tiên sau dòng `Action Input:` (có thể nằm trong khối ```json,
      có thể có chữ thừa phía sau). Thiếu tên tool, thiếu `Action Input:`, JSON hỏng hoặc không phải object ->
      ReActParseError có thông điệp đủ để model tự sửa.
    - Ngược lại có `Final Answer:`: trả Final với toàn bộ phần sau nó (nhiều dòng), rỗng -> ReActParseError.
    - Không có cả hai -> ReActParseError.
    - Từ khoá đứng đầu dòng (cho phép khoảng trắng phía trước), không phân biệt hoa thường. `thought` là phần sau
      `Thought:` tới trước dòng Action/Final Answer, không có thì "".
    """
    # TODO
    raise NotImplementedError


def run_react(llm, task: str, registry, *, max_steps: int = 8, max_format_retries: int = 2, max_repeats: int = 2,
              system: str | None = None, history: list[dict] | None = None) -> RunResult:
    """Chạy vòng ReAct, trả RunResult. Quy tắc chi tiết ở README của bài.

    llm: có .chat(messages) -> str (llmkit client hoặc FakeLLM).
    registry: có .specs() -> list[spec] và .call(tool, args) -> object có .ok, .content (như ToolRegistry bài 01).
    """
    # TODO
    raise NotImplementedError
