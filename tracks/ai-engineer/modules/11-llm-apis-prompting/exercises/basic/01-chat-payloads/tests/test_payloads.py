import copy
import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)

TOOLS = [{
    "type": "function",
    "function": {
        "name": "count_feedback",
        "description": "Đếm số phản hồi theo chủ đề và cảm xúc.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string"}, "sentiment": {"type": "string"}},
                       "required": ["topic"]},
    },
}]

CONVERSATION = [
    {"role": "system", "content": "Bạn là trợ lý phân tích phản hồi sinh viên."},
    {"role": "system", "content": "Trả lời tiếng Việt."},
    {"role": "user", "content": "Có bao nhiêu phản hồi tiêu cực về cơ sở vật chất và về giảng viên?"},
    {"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_1", "type": "function",
         "function": {"name": "count_feedback", "arguments": '{"topic": "facility", "sentiment": "negative"}'}},
        {"id": "call_2", "type": "function",
         "function": {"name": "count_feedback", "arguments": '{"topic": "lecturer", "sentiment": "negative"}'}},
    ]},
    {"role": "tool", "tool_call_id": "call_1", "content": "102"},
    {"role": "tool", "tool_call_id": "call_2", "content": "1032"},
    {"role": "assistant", "content": "Có 102 phản hồi tiêu cực về cơ sở vật chất và 1032 về giảng viên."},
    {"role": "user", "content": "Cảm ơn."},
]


@pytest.fixture(scope="module")
def p():
    return ex.module("payloads.py")


# ---------- to_anthropic ----------

def test_anthropic_system_is_top_level(p):
    body = p.to_anthropic(CONVERSATION, TOOLS, model="claude-haiku-5-5", max_tokens=256)
    assert body["model"] == "claude-haiku-5-5" and body["max_tokens"] == 256
    assert body["system"] == "Bạn là trợ lý phân tích phản hồi sinh viên.\n\nTrả lời tiếng Việt."
    assert all(m["role"] in ("user", "assistant") for m in body["messages"]), "Messages API không có role system/tool"
    assert body["messages"][0] == {"role": "user", "content": CONVERSATION[2]["content"]}


def test_anthropic_tool_use_blocks(p):
    body = p.to_anthropic(CONVERSATION, TOOLS, model="m")
    assistant = body["messages"][1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == [
        {"type": "tool_use", "id": "call_1", "name": "count_feedback",
         "input": {"topic": "facility", "sentiment": "negative"}},
        {"type": "tool_use", "id": "call_2", "name": "count_feedback",
         "input": {"topic": "lecturer", "sentiment": "negative"}},
    ], "content None thì không có khối text; arguments (chuỗi JSON) thành input (dict)"


def test_anthropic_parallel_tool_results_in_one_user_message(p):
    body = p.to_anthropic(CONVERSATION, TOOLS, model="m")
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant", "user", "assistant", "user"], \
        "hai message tool liên tiếp phải gom vào MỘT message user"
    results = body["messages"][2]["content"]
    assert results == [
        {"type": "tool_result", "tool_use_id": "call_1", "content": "102"},
        {"type": "tool_result", "tool_use_id": "call_2", "content": "1032"},
    ]
    assert body["messages"][3]["content"] == [{"type": "text", "text": CONVERSATION[6]["content"]}]
    assert body["messages"][4] == {"role": "user", "content": "Cảm ơn."}


def test_anthropic_tools_schema(p):
    body = p.to_anthropic(CONVERSATION, TOOLS, model="m")
    assert body["tools"] == [{"name": "count_feedback", "description": "Đếm số phản hồi theo chủ đề và cảm xúc.",
                              "input_schema": TOOLS[0]["function"]["parameters"]}]
    plain = p.to_anthropic([{"role": "user", "content": "Xin chào"}], model="m")
    assert "tools" not in plain and "system" not in plain, "không có tool/system thì không gửi khoá đó"
    assert plain["max_tokens"] == 1024


def test_anthropic_assistant_text_and_tool_call(p):
    msgs = [{"role": "user", "content": "Đếm giúp tôi."},
            {"role": "assistant", "content": "Để tôi đếm.", "tool_calls": [
                {"id": "c9", "type": "function", "function": {"name": "count_feedback", "arguments": {"topic": "others"}}}]},
            {"role": "tool", "tool_call_id": "c9", "content": "5"}]
    body = p.to_anthropic(msgs, model="m")
    assert body["messages"][1]["content"] == [
        {"type": "text", "text": "Để tôi đếm."},
        {"type": "tool_use", "id": "c9", "name": "count_feedback", "input": {"topic": "others"}},
    ], "arguments đã là dict (kiểu Ollama) thì giữ nguyên"


def test_anthropic_does_not_mutate_input(p):
    before = copy.deepcopy(CONVERSATION)
    p.to_anthropic(CONVERSATION, TOOLS, model="m")
    assert CONVERSATION == before


def test_anthropic_rejects_bad_input(p):
    bad_json = copy.deepcopy(CONVERSATION[:4])
    bad_json[3]["tool_calls"][0]["function"]["arguments"] = '{"topic": "facility"'
    with pytest.raises(ValueError):
        p.to_anthropic(bad_json, model="m")
    orphan = [{"role": "user", "content": "x"}, {"role": "tool", "tool_call_id": "call_404", "content": "1"}]
    with pytest.raises(ValueError):
        p.to_anthropic(orphan, model="m")
    not_object = copy.deepcopy(CONVERSATION[:4])
    not_object[3]["tool_calls"][0]["function"]["arguments"] = '["facility"]'
    with pytest.raises(ValueError):
        p.to_anthropic(not_object, model="m")


# ---------- parse_* ----------

OPENAI_TOOL = {
    "id": "chatcmpl-1", "object": "chat.completion", "model": "gpt-x",
    "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
        "role": "assistant", "content": None, "tool_calls": [
            {"id": "call_a", "type": "function",
             "function": {"name": "count_feedback", "arguments": "{\"topic\": \"facility\"}"}}]}}],
    "usage": {"prompt_tokens": 91, "completion_tokens": 17, "total_tokens": 108},
}
OPENAI_TEXT = {
    "id": "chatcmpl-2", "object": "chat.completion", "model": "gpt-x",
    "choices": [{"index": 0, "finish_reason": "length", "message": {"role": "assistant", "content": "Có 102 phản"}}],
    "usage": {"prompt_tokens": 120, "completion_tokens": 4, "total_tokens": 124},
}
ANTHROPIC_TOOL = {
    "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-x", "stop_reason": "tool_use",
    "content": [{"type": "text", "text": "Tôi sẽ đếm. "},
                {"type": "tool_use", "id": "toolu_1", "name": "count_feedback", "input": {"topic": "facility"}},
                {"type": "tool_use", "id": "toolu_2", "name": "count_feedback", "input": {"topic": "lecturer"}}],
    "usage": {"input_tokens": 300, "output_tokens": 55},
}
ANTHROPIC_TEXT = {
    "id": "msg_2", "type": "message", "role": "assistant", "model": "claude-x", "stop_reason": "end_turn",
    "content": [{"type": "text", "text": "Có 102 phản hồi"}, {"type": "text", "text": " tiêu cực."}],
    "usage": {"input_tokens": 400, "output_tokens": 9},
}
OLLAMA_TOOL = {
    "model": "qwen2.5:3b", "done": True, "done_reason": "stop",
    "message": {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "count_feedback", "arguments": {"topic": "facility", "sentiment": "negative"}}},
        {"function": {"name": "count_feedback", "arguments": {"topic": "lecturer"}}}]},
    "prompt_eval_count": 210, "eval_count": 40,
}
OLLAMA_LENGTH = {"model": "qwen2.5:3b", "done": True, "done_reason": "length",
                 "message": {"role": "assistant", "content": "Có 102"}, "prompt_eval_count": 50, "eval_count": 3}


def test_parse_openai(p):
    r = p.parse_openai(OPENAI_TOOL)
    assert r.text == "" and r.finish_reason == "tool_calls"
    assert [(c.id, c.name, c.arguments) for c in r.tool_calls] == [("call_a", "count_feedback", {"topic": "facility"})]
    assert (r.prompt_tokens, r.completion_tokens) == (91, 17)
    t = p.parse_openai(OPENAI_TEXT)
    assert (t.text, t.finish_reason, t.tool_calls, t.prompt_tokens) == ("Có 102 phản", "length", [], 120)


def test_parse_anthropic(p):
    r = p.parse_anthropic(ANTHROPIC_TOOL)
    assert r.text == "Tôi sẽ đếm. " and r.finish_reason == "tool_calls"
    assert [(c.id, c.name, c.arguments) for c in r.tool_calls] == [
        ("toolu_1", "count_feedback", {"topic": "facility"}), ("toolu_2", "count_feedback", {"topic": "lecturer"})]
    assert (r.prompt_tokens, r.completion_tokens) == (300, 55)
    t = p.parse_anthropic(ANTHROPIC_TEXT)
    assert t.text == "Có 102 phản hồi tiêu cực." and t.finish_reason == "stop" and t.tool_calls == []
    assert p.parse_anthropic({**ANTHROPIC_TEXT, "stop_reason": "max_tokens"}).finish_reason == "length"
    assert p.parse_anthropic({**ANTHROPIC_TEXT, "stop_reason": "stop_sequence"}).finish_reason == "stop"


def test_parse_ollama(p):
    r = p.parse_ollama(OLLAMA_TOOL)
    assert r.finish_reason == "tool_calls", "Ollama báo done_reason 'stop' cả khi gọi tool: phải tự suy ra"
    assert [(c.id, c.name, c.arguments) for c in r.tool_calls] == [
        ("call_0", "count_feedback", {"topic": "facility", "sentiment": "negative"}),
        ("call_1", "count_feedback", {"topic": "lecturer"})]
    assert (r.prompt_tokens, r.completion_tokens) == (210, 40)
    t = p.parse_ollama(OLLAMA_LENGTH)
    assert (t.text, t.finish_reason, t.tool_calls) == ("Có 102", "length", [])
    with_id = json.loads(json.dumps(OLLAMA_TOOL))
    with_id["message"]["tool_calls"][0]["id"] = "abc"
    assert p.parse_ollama(with_id).tool_calls[0].id == "abc", "id có sẵn thì giữ"


def test_parse_rejects_bad_arguments(p):
    bad = json.loads(json.dumps(OPENAI_TOOL))
    bad["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{topic: facility}"
    with pytest.raises(ValueError):
        p.parse_openai(bad)


def test_round_trip_openai_reply_into_anthropic_history(p):
    r = p.parse_openai(OPENAI_TOOL)
    history = [{"role": "user", "content": "Đếm."},
               {"role": "assistant", "content": r.text or None,
                "tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                               for c in r.tool_calls]},
               {"role": "tool", "tool_call_id": "call_a", "content": "102"}]
    body = p.to_anthropic(history, TOOLS, model="m")
    assert body["messages"][1]["content"][0]["input"] == {"topic": "facility"}
    assert body["messages"][2]["content"][0]["tool_use_id"] == "call_a"
