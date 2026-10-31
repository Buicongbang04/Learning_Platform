import copy
import json

import pandas as pd
import pytest

from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)

# 8 dòng giả kiểu UIT-VSFC: sentiment 0 neg, 1 neu, 2 pos; topic 0 lecturer, 1 training_program, 2 facility, 3 others
DF = pd.DataFrame({
    "sentence": ["phòng nóng", "thầy dạy hay", "wifi yếu", "máy chiếu mờ", "không ý kiến", "cô vui tính",
                 "môn học nặng", "bàn ghế cũ"],
    "sentiment": [0, 2, 0, 0, 1, 2, 0, 0],
    "topic": [2, 0, 2, 2, 3, 0, 1, 2],
})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("tools.ipynb")


def call(name, arguments, id_="c1"):
    return {"id": id_, "type": "function", "function": {"name": name, "arguments": arguments}}


# ---------- registry ----------

def test_registry(nb):
    reg = nb.make_registry(DF)
    assert set(reg) == {"count_feedback", "percentage", "list_examples"}
    assert reg["count_feedback"]() == {"count": 8}
    assert reg["count_feedback"](topic="facility") == {"count": 4}
    assert reg["count_feedback"](topic="facility", sentiment="negative") == {"count": 4}
    assert reg["count_feedback"](sentiment="positive") == {"count": 2}
    assert reg["count_feedback"](topic="others", sentiment="negative") == {"count": 0}
    assert type(reg["count_feedback"]()["count"]) is int, "count phải là int Python để json.dumps được"
    assert reg["percentage"](part=138, whole=145) == {"percent": 95.2}
    with pytest.raises(ValueError):
        reg["percentage"](part=1, whole=0)
    assert reg["list_examples"](topic="facility", sentiment="negative", limit=2) == {
        "sentences": ["phòng nóng", "wifi yếu"]}
    assert reg["list_examples"](topic="facility", sentiment="negative") == {
        "sentences": ["phòng nóng", "wifi yếu", "máy chiếu mờ"]}, "limit mặc định 3"


# ---------- execute_tool_call ----------

def test_execute_ok(nb):
    reg = nb.make_registry(DF)
    out = nb.execute_tool_call(call("count_feedback", '{"topic": "facility"}'), nb.TOOLS, reg)
    assert json.loads(out) == {"count": 4}
    out = nb.execute_tool_call(call("count_feedback", {"sentiment": "positive"}), nb.TOOLS, reg)
    assert json.loads(out) == {"count": 2}, "arguments dạng dict (Ollama)"
    out = nb.execute_tool_call(call("list_examples", {"topic": "others", "sentiment": "neutral"}), nb.TOOLS, reg)
    assert "không ý kiến" in out, "ensure_ascii=False: tiếng Việt giữ nguyên trong kết quả"


@pytest.mark.parametrize("c, must_contain", [
    (call("count_comments", {}), "count_feedback"),
    (call("count_feedback", '{"topic": "facility"'), "count_feedback"),
    (call("count_feedback", '["facility"]'), "count_feedback"),
    (call("count_feedback", {"topic": "phòng học"}), "phòng học"),
    (call("count_feedback", {"topic": "facility", "year": 2024}), "year"),
    (call("percentage", {"part": 3}), "whole"),
    (call("list_examples", {"topic": "facility", "sentiment": "negative", "limit": 9}), "9"),
    (call("percentage", {"part": 3, "whole": 0}), "whole"),
])
def test_execute_errors_are_messages(nb, c, must_contain):
    reg = nb.make_registry(DF)
    out = nb.execute_tool_call(c, nb.TOOLS, reg)
    assert isinstance(out, str) and out.startswith("ERROR: "), out
    assert must_contain in out, f"thông báo lỗi phải đủ để model tự sửa: {out!r}"


# ---------- run_tool_loop ----------

def scripted(*replies):
    """chat(messages, tools) phát lần lượt các message assistant; ghi lại lịch sử mỗi lần gọi."""
    fake = FakeLLM([json.dumps(r, ensure_ascii=False) for r in replies])
    seen_tools = []

    def chat(messages, tools):
        seen_tools.append(tools)
        return json.loads(fake.chat(copy.deepcopy(messages)))

    return chat, fake, seen_tools


Q = [{"role": "system", "content": "Trợ lý."}, {"role": "user", "content": "Tỉ lệ tiêu cực về cơ sở vật chất?"}]


def test_loop_two_tools_then_answer(nb):
    reg = nb.make_registry(DF)
    chat, fake, seen_tools = scripted(
        {"role": "assistant", "content": None, "tool_calls": [
            call("count_feedback", '{"topic": "facility", "sentiment": "negative"}', "a"),
            call("count_feedback", '{"topic": "facility"}', "b")]},
        {"role": "assistant", "content": "", "tool_calls": [call("percentage", {"part": 4, "whole": 4}, "c")]},
        {"role": "assistant", "content": "100% phản hồi về cơ sở vật chất là tiêu cực."},
    )
    before = copy.deepcopy(Q)
    res = nb.run_tool_loop(chat, Q, nb.TOOLS, reg, max_steps=5)
    assert Q == before, "không sửa messages đầu vào"
    assert res.answer == "100% phản hồi về cơ sở vật chất là tiêu cực." and res.stopped == "answer"
    assert res.steps == 3 and res.errors == 0
    assert all(t is nb.TOOLS or t == nb.TOOLS for t in seen_tools)
    assert [(n, a) for n, a, _ in res.tool_calls] == [
        ("count_feedback", {"topic": "facility", "sentiment": "negative"}), ("count_feedback", {"topic": "facility"}),
        ("percentage", {"part": 4, "whole": 4})]
    second = fake.calls[1]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "tool", "tool"]
    assert second[3] == {"role": "tool", "tool_call_id": "a", "name": "count_feedback", "content": '{"count": 4}'}
    assert second[4]["tool_call_id"] == "b"
    assert res.messages[:2] == Q and res.messages[-1] == {"role": "assistant", "content": res.answer}
    assert len(res.messages) == 2 + 3 + 2 + 1


def test_loop_assigns_missing_ids(nb):
    reg = nb.make_registry(DF)
    chat, fake, _ = scripted(
        {"role": "assistant", "content": None, "tool_calls": [
            {"type": "function", "function": {"name": "count_feedback", "arguments": {}}},
            {"type": "function", "function": {"name": "count_feedback", "arguments": {"sentiment": "neutral"}}}]},
        {"role": "assistant", "content": None, "tool_calls": [
            {"type": "function", "function": {"name": "count_feedback", "arguments": {"topic": "others"}}}]},
        {"role": "assistant", "content": "Xong."},
    )
    res = nb.run_tool_loop(chat, Q, nb.TOOLS, reg)
    assistant_ids = [[c["id"] for c in m["tool_calls"]] for m in res.messages if m.get("tool_calls")]
    assert assistant_ids == [["call_0_0", "call_0_1"], ["call_1_0"]]
    tool_ids = [m["tool_call_id"] for m in res.messages if m["role"] == "tool"]
    assert tool_ids == ["call_0_0", "call_0_1", "call_1_0"]


def test_loop_errors_go_back_to_model(nb):
    reg = nb.make_registry(DF)
    chat, fake, _ = scripted(
        {"role": "assistant", "content": None, "tool_calls": [call("count_feedback", {"topic": "phòng học"}, "x")]},
        {"role": "assistant", "content": None, "tool_calls": [call("count_feedback", {"topic": "facility"}, "y")]},
        {"role": "assistant", "content": "Có 4 phản hồi."},
    )
    res = nb.run_tool_loop(chat, Q, nb.TOOLS, reg)
    assert res.errors == 1 and res.answer == "Có 4 phản hồi."
    assert fake.calls[1][-1]["content"].startswith("ERROR: "), "lỗi được gửi lại cho model như kết quả tool"
    assert res.tool_calls[0][2].startswith("ERROR: ") and res.tool_calls[1][2] == '{"count": 4}'


def test_loop_bad_json_recorded_raw(nb):
    reg = nb.make_registry(DF)
    chat, _, _ = scripted(
        {"role": "assistant", "content": None, "tool_calls": [call("count_feedback", '{"topic": ', "z")]},
        {"role": "assistant", "content": "Không đếm được."},
    )
    res = nb.run_tool_loop(chat, Q, nb.TOOLS, reg)
    assert res.tool_calls[0][1] == '{"topic": ', "arguments hỏng giữ nguyên văn trong tool_calls"
    assert res.errors == 1


def test_loop_max_steps(nb):
    reg = nb.make_registry(DF)
    looping = {"role": "assistant", "content": None, "tool_calls": [call("count_feedback", {}, "k")]}
    chat, fake, _ = scripted(*[looping] * 10)
    res = nb.run_tool_loop(chat, Q, nb.TOOLS, reg, max_steps=3)
    assert res.stopped == "max_steps" and res.answer is None
    assert res.steps == 3 and len(fake.calls) == 3, "gọi chat đúng max_steps lần"
    assert len(res.tool_calls) == 3, "tool của lần cuối vẫn được thực thi"


def test_loop_direct_answer(nb):
    reg = nb.make_registry(DF)
    chat, _, _ = scripted({"role": "assistant", "content": "Tôi không có dữ liệu thời tiết."})
    res = nb.run_tool_loop(chat, Q, nb.TOOLS, reg)
    assert (res.answer, res.steps, res.tool_calls, res.stopped) == ("Tôi không có dữ liệu thời tiết.", 1, [], "answer")


# ---------- prompted_chat ----------

class SchemaLLM(FakeLLM):
    def __init__(self, replies):
        super().__init__(replies)
        self.schemas = []

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None):
        self.schemas.append(json_schema)
        return super().chat(messages, model=model, temperature=temperature, json_schema=json_schema)


def test_prompted_protocol_and_tool_call(nb):
    llm = SchemaLLM(['{"tool_calls": [{"name": "count_feedback", "arguments": {"topic": "facility"}}]}'])
    reply = nb.prompted_chat(llm)(Q, nb.TOOLS)
    assert llm.schemas == [nb.PROMPTED_SCHEMA]
    sent = llm.calls[0]
    assert sent[0]["role"] == "system" and sent[1:] == Q, "system giao thức đứng đầu, rồi đúng messages của người gọi"
    protocol = sent[0]["content"]
    for tool in nb.TOOLS:
        f = tool["function"]
        assert f["name"] in protocol and f["description"] in protocol
        assert json.dumps(f["parameters"], ensure_ascii=False) in protocol
    assert "tool_calls" in protocol and "answer" in protocol
    assert reply == {"role": "assistant", "content": None, "tool_calls": [
        {"type": "function", "function": {"name": "count_feedback", "arguments": {"topic": "facility"}}}]}


def test_prompted_history_conversion(nb):
    history = Q + [
        {"role": "assistant", "content": None, "tool_calls": [call("count_feedback", {"topic": "facility"}, "a")]},
        {"role": "tool", "tool_call_id": "a", "name": "count_feedback", "content": '{"count": 4}'},
    ]
    llm = SchemaLLM(['{"answer": "Có 4 phản hồi."}'])
    reply = nb.prompted_chat(llm)(history, nb.TOOLS)
    sent = llm.calls[0]
    assert sent[3] == {"role": "assistant", "content": json.dumps(
        {"tool_calls": [{"name": "count_feedback", "arguments": {"topic": "facility"}}]}, ensure_ascii=False)}
    assert sent[4] == {"role": "user", "content": 'Kết quả tool count_feedback (a): {"count": 4}'}
    assert all(set(m) == {"role", "content"} for m in sent), "LLM chỉ-có-chuỗi: mỗi message chỉ có role và content"
    assert reply == {"role": "assistant", "content": "Có 4 phản hồi."}


@pytest.mark.parametrize("raw, content", [
    ("Có 4 phản hồi tiêu cực.", "Có 4 phản hồi tiêu cực."),
    ('{"tool_calls": [], "answer": "Bốn."}', "Bốn."),
    ('["không phải object"]', '["không phải object"]'),
])
def test_prompted_plain_answers(nb, raw, content):
    reply = nb.prompted_chat(SchemaLLM([raw]))(Q, nb.TOOLS)
    assert reply["content"] == content and not reply.get("tool_calls")


def test_prompted_end_to_end_with_loop(nb):
    reg = nb.make_registry(DF)
    llm = SchemaLLM([
        '{"tool_calls": [{"name": "count_feedback", "arguments": {"topic": "facility", "sentiment": "negative"}},'
        ' {"name": "count_feedback", "arguments": {"topic": "facility"}}]}',
        '{"tool_calls": [{"name": "percentage", "arguments": {"part": 4, "whole": 4}}]}',
        '{"answer": "100%."}',
    ])
    res = nb.run_tool_loop(nb.prompted_chat(llm), Q, nb.TOOLS, reg)
    assert res.answer == "100%." and res.steps == 3 and res.errors == 0
    assert "Kết quả tool percentage (call_1_0): " in llm.calls[2][-1]["content"]
    assert '{"percent": 100.0}' in llm.calls[2][-1]["content"]
