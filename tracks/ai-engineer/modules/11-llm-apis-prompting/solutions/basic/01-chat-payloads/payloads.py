"""Chuyển request/response giữa ba "phương ngữ" của Chat API: OpenAI Chat Completions, Anthropic Messages, Ollama.

Dạng chuẩn nội bộ của bài là message kiểu OpenAI Chat Completions (`system`, `user`, `assistant` có thể kèm
`tool_calls`, `tool`). Mọi response được đưa về một `Reply` chung để code phía sau không phụ thuộc nhà cung cấp.
Chỉ dùng thư viện chuẩn.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Reply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0


ANTHROPIC_STOP = {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length", "tool_use": "tool_calls"}


def _arguments(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"arguments không phải JSON hợp lệ: {raw!r}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"arguments phải là JSON object, nhận {type(value).__name__}")
    return value


def to_anthropic(messages: list[dict], tools: list[dict] | None = None, *, model: str, max_tokens: int = 1024) -> dict:
    system_parts: list[str] = []
    out: list[dict] = []
    known_ids: set[str] = set()
    for msg in messages:
        role = msg["role"]
        if role == "system":
            system_parts.append(msg["content"])
        elif role == "user":
            out.append({"role": "user", "content": msg["content"]})
        elif role == "assistant":
            blocks = []
            if msg.get("content"):
                blocks.append({"type": "text", "text": msg["content"]})
            for call in msg.get("tool_calls") or []:
                known_ids.add(call["id"])
                blocks.append({"type": "tool_use", "id": call["id"], "name": call["function"]["name"],
                               "input": _arguments(call["function"]["arguments"])})
            out.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            if msg["tool_call_id"] not in known_ids:
                raise ValueError(f"tool_call_id {msg['tool_call_id']!r} không ứng với tool call nào trước đó")
            block = {"type": "tool_result", "tool_use_id": msg["tool_call_id"], "content": msg["content"]}
            prev = out[-1] if out else None
            if prev and prev["role"] == "user" and isinstance(prev["content"], list):
                prev["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
        else:
            raise ValueError(f"role không hỗ trợ: {role!r}")
    body: dict = {"model": model, "max_tokens": max_tokens, "messages": out}
    if system_parts:
        body["system"] = "\n\n".join(system_parts)
    if tools:
        body["tools"] = [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
                          "input_schema": t["function"]["parameters"]} for t in tools]
    return body


def parse_openai(resp: dict) -> Reply:
    choice = resp["choices"][0]
    msg = choice["message"]
    calls = [ToolCall(c["id"], c["function"]["name"], _arguments(c["function"]["arguments"]))
             for c in msg.get("tool_calls") or []]
    usage = resp.get("usage") or {}
    return Reply(msg.get("content") or "", calls, choice["finish_reason"],
                 usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


def parse_anthropic(resp: dict) -> Reply:
    texts, calls = [], []
    for block in resp["content"]:
        if block["type"] == "text":
            texts.append(block["text"])
        elif block["type"] == "tool_use":
            calls.append(ToolCall(block["id"], block["name"], _arguments(block["input"])))
    usage = resp.get("usage") or {}
    reason = ANTHROPIC_STOP.get(resp["stop_reason"], resp["stop_reason"])
    return Reply("".join(texts), calls, reason, usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def parse_ollama(resp: dict) -> Reply:
    msg = resp["message"]
    calls = []
    for i, c in enumerate(msg.get("tool_calls") or []):
        calls.append(ToolCall(c.get("id") or f"call_{i}", c["function"]["name"], _arguments(c["function"]["arguments"])))
    if calls:
        reason = "tool_calls"
    elif resp.get("done_reason") == "length":
        reason = "length"
    else:
        reason = "stop"
    return Reply(msg.get("content") or "", calls, reason, resp.get("prompt_eval_count", 0), resp.get("eval_count", 0))
