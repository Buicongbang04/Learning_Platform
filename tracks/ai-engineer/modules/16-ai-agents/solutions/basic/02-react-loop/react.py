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


_OBSERVATION = re.compile(r"^\s*Observation\s*:", re.I | re.M)
_ACTION = re.compile(r"^\s*Action\s*:[ \t]*(.*)$", re.I | re.M)
_INPUT = re.compile(r"^\s*Action\s+Input\s*:", re.I | re.M)
_FINAL = re.compile(r"^\s*Final\s+Answer\s*:", re.I | re.M)
_THOUGHT = re.compile(r"^\s*Thought\s*:(.*?)(?=^\s*(?:Action|Final\s+Answer)\b|\Z)", re.I | re.M | re.S)
_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```\s*$")


def clean_reply(text: str) -> str:
    match = _OBSERVATION.search(text)
    return (text[: match.start()] if match else text).strip()


def parse_react(text: str) -> Action | Final:
    text = clean_reply(text)
    thought_match = _THOUGHT.search(text)
    thought = thought_match.group(1).strip() if thought_match else ""
    action = _ACTION.search(text)
    final = _FINAL.search(text)
    if action and (not final or action.start() < final.start()):
        tool = action.group(1).strip().strip("`'\"*").strip()
        if not tool:
            raise ReActParseError("Dòng `Action:` thiếu tên tool.")
        inp = _INPUT.search(text, action.end())
        if not inp:
            raise ReActParseError(f"Thiếu dòng `Action Input:` (JSON object) cho tool {tool}.")
        end = final.start() if final and final.start() > inp.end() else len(text)
        raw = _FENCE.sub("", text[inp.end():end].strip()).strip()
        try:
            args, _ = json.JSONDecoder().raw_decode(raw)
        except ValueError:
            raise ReActParseError(f"`Action Input` của {tool} không phải JSON hợp lệ: {raw[:80]!r}.") from None
        if not isinstance(args, dict):
            raise ReActParseError(f"`Action Input` của {tool} phải là JSON object, nhận {raw[:80]!r}.")
        return Action(tool, args, thought)
    if final:
        answer = text[final.end():].strip()
        if not answer:
            raise ReActParseError("`Final Answer:` rỗng.")
        return Final(answer, thought)
    raise ReActParseError("Không thấy `Action:` hoặc `Final Answer:`.")


def run_react(llm, task: str, registry, *, max_steps: int = 8, max_format_retries: int = 2, max_repeats: int = 2,
              system: str | None = None, history: list[dict] | None = None) -> RunResult:
    prompt = (system or SYSTEM_TEMPLATE).format(tools=render_tools(registry.specs()))
    messages = [{"role": "system", "content": prompt}, *[dict(m) for m in history or []],
                {"role": "user", "content": task}]
    result = RunResult(None, "max_steps", [], messages)
    consecutive_format = 0
    last_key = None
    repeats = 0
    for index in range(max_steps):
        start = time.perf_counter()
        try:
            reply = llm.chat(messages)
        except llmkit.LLMError as exc:
            result.stopped, result.error = "llm_error", str(exc)
            return result
        try:
            parsed = parse_react(reply)
        except ReActParseError as exc:
            consecutive_format += 1
            result.format_errors += 1
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"Lỗi định dạng: {exc} Trả lời lại đúng định dạng."})
            result.steps.append(Step(index, "format_error", reply, observation=str(exc), ok=False,
                                     seconds=time.perf_counter() - start))
            if consecutive_format > max_format_retries:
                result.stopped = "format_error"
                return result
            continue
        consecutive_format = 0
        cleaned = clean_reply(reply)
        if isinstance(parsed, Final):
            messages.append({"role": "assistant", "content": cleaned})
            result.steps.append(Step(index, "final", reply, seconds=time.perf_counter() - start))
            result.answer, result.stopped = parsed.answer, "answer"
            return result
        key = (parsed.tool, json.dumps(parsed.args, sort_keys=True, ensure_ascii=False))
        repeats = repeats + 1 if key == last_key else 0
        last_key = key
        if repeats >= max_repeats:
            result.steps.append(Step(index, "repeat", reply, parsed.tool, parsed.args, ok=False,
                                     seconds=time.perf_counter() - start))
            result.stopped = "repeated_action"
            return result
        obs = registry.call(parsed.tool, parsed.args)
        result.tool_errors += not obs.ok
        messages.append({"role": "assistant", "content": cleaned})
        messages.append({"role": "user", "content": f"Observation: {obs.content}"})
        result.steps.append(Step(index, "action", reply, parsed.tool, parsed.args, obs.content, obs.ok,
                                 time.perf_counter() - start))
    return result
