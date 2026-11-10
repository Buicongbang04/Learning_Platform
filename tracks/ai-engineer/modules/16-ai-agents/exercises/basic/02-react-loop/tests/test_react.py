import json
from dataclasses import dataclass

import pytest

import llmkit
from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def r():
    return ex.module("react.py")


class Fake(FakeLLM):
    """FakeLLM lưu BẢN SAO messages của mỗi lời gọi (run_react được phép nối thêm vào cùng một list)."""

    def chat(self, messages, **kwargs):
        reply = super().chat(messages, **kwargs)
        self.calls[-1] = [dict(m) for m in messages]
        return reply


@dataclass
class Obs:
    ok: bool
    content: str


class Registry:
    """Registry giả: hai tool, đếm số lần gọi."""

    def __init__(self):
        self.calls = []

    def specs(self):
        return [{"type": "function", "function": {"name": "search_books", "description": "Tìm sách theo tên.",
                 "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
                {"type": "function", "function": {"name": "calculator", "description": "Tính biểu thức.",
                 "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}}}]

    def call(self, name, args):
        self.calls.append((name, args))
        if name == "search_books":
            return Obs(True, json.dumps([{"id": "B02", "title": "Tắt đèn", "price": 55000}], ensure_ascii=False))
        if name == "calculator":
            if "x" in args.get("expression", ""):
                return Obs(False, "ERROR: calculator lỗi khi chạy: ValueError: chỉ nhận số")
            return Obs(True, "165000")
        return Obs(False, f"ERROR: không có tool {name!r}.")


ACT_SEARCH = 'Thought: tìm giá sách\nAction: search_books\nAction Input: {"query": "Tắt đèn"}'
ACT_CALC = 'Thought: nhân 3\nAction: calculator\nAction Input: {"expression": "3 * 55000"}'
FINAL = "Thought: đủ rồi\nFinal Answer: 3 cuốn 'Tắt đèn' hết 165.000 đồng."


# ---------- parse_react ----------


def test_parse_action(r):
    a = r.parse_react(ACT_SEARCH)
    assert isinstance(a, r.Action)
    assert (a.tool, a.args, a.thought) == ("search_books", {"query": "Tắt đèn"}, "tìm giá sách")


def test_parse_final_multiline(r):
    f = r.parse_react("Thought: xong\nFinal Answer: Dòng một.\nDòng hai.")
    assert isinstance(f, r.Final)
    assert f.answer == "Dòng một.\nDòng hai." and f.thought == "xong"
    assert r.parse_react("Final Answer: 42").thought == ""


def test_parse_cuts_hallucinated_observation(r):
    text = ACT_SEARCH + '\nObservation: [{"price": 99999}]\nThought: xong\nFinal Answer: 99.999 đồng'
    a = r.parse_react(text)
    assert isinstance(a, r.Action) and a.args == {"query": "Tắt đèn"}
    assert r.clean_reply(text) == ACT_SEARCH
    assert r.clean_reply("  Final Answer: ok  ") == "Final Answer: ok"


def test_parse_first_keyword_wins(r):
    assert isinstance(r.parse_react("Final Answer: không cần tool\nAction: calculator\nAction Input: {}"), r.Final)
    assert isinstance(r.parse_react('Action: calculator\nAction Input: {"expression": "1+1"}\nFinal Answer: 2'), r.Action)


@pytest.mark.parametrize("text, args", [
    ('Action: calculator\nAction Input: ```json\n{"expression": "2*3"}\n```', {"expression": "2*3"}),
    ('Action: calculator\nAction Input: {"expression": "2*3"} rồi chờ kết quả', {"expression": "2*3"}),
    ('Action: search_books\nAction Input:\n{\n  "query": "Số đỏ",\n  "filters": {"year": [1936]}\n}',
     {"query": "Số đỏ", "filters": {"year": [1936]}}),
    ("  thought: x\n  ACTION: calculator\n  action input: {}", {}),
])
def test_parse_action_input_variants(r, text, args):
    a = r.parse_react(text)
    assert isinstance(a, r.Action) and a.args == args


def test_parse_tool_name_cleanup(r):
    assert r.parse_react("Action: `calculator`\nAction Input: {}").tool == "calculator"
    assert r.parse_react('Action: **"search_books"**\nAction Input: {"query": "a"}').tool == "search_books"


@pytest.mark.parametrize("text, hint", [
    ("Action: calculator", "Action Input"),
    ("Action: \nAction Input: {}", "tool"),
    ('Action: calculator\nAction Input: {"expression": 2*3}', "JSON"),
    ('Action: calculator\nAction Input: ["2*3"]', "object"),
    ("Final Answer:   ", "rỗng"),
    ("Tôi nghĩ giá là 55.000 đồng.", "Final Answer"),
    ('Action Input: {"query": "x"}', "Action"),
])
def test_parse_errors(r, text, hint):
    with pytest.raises(r.ReActParseError) as info:
        r.parse_react(text)
    assert hint.lower() in str(info.value).lower(), f"thông điệp lỗi nên nhắc tới {hint!r}"


# ---------- run_react ----------


def test_run_happy_path(r):
    reg = Registry()
    fake = Fake([ACT_SEARCH, ACT_CALC, FINAL])
    res = r.run_react(fake, "Mua 3 cuốn Tắt đèn hết bao nhiêu?", reg)
    assert res.stopped == "answer" and res.answer == "3 cuốn 'Tắt đèn' hết 165.000 đồng."
    assert reg.calls == [("search_books", {"query": "Tắt đèn"}), ("calculator", {"expression": "3 * 55000"})]
    assert [s.kind for s in res.steps] == ["action", "action", "final"]
    assert [s.index for s in res.steps] == [0, 1, 2]
    assert res.steps[1].observation == "165000" and res.steps[1].ok is True and res.steps[1].tool == "calculator"
    assert all(s.seconds >= 0 for s in res.steps)
    assert len(fake.calls) == 3 and res.tool_errors == 0 and res.format_errors == 0


def test_run_messages_layout(r):
    reg = Registry()
    fake = Fake([ACT_SEARCH + "\nObservation: bịa", FINAL])
    res = r.run_react(fake, "Giá Tắt đèn?", reg)
    m = res.messages
    assert m[0]["role"] == "system" and m[0]["content"] == r.SYSTEM_TEMPLATE.format(tools=r.render_tools(reg.specs()))
    assert m[1] == {"role": "user", "content": "Giá Tắt đèn?"}
    assert m[2] == {"role": "assistant", "content": ACT_SEARCH}, "lưu lượt đã bỏ Observation bịa"
    assert m[3]["role"] == "user" and m[3]["content"].startswith("Observation: ")
    assert "Tắt đèn" in m[3]["content"] and "bịa" not in m[3]["content"]
    assert m[4] == {"role": "assistant", "content": FINAL}
    second_call = fake.calls[1]
    assert second_call[:4] == m[:4], "lượt 2 thấy system, task, lượt 1 và Observation thật"


def test_run_tool_error_goes_back_to_model(r):
    reg = Registry()
    bad = 'Action: calculator\nAction Input: {"expression": "3x55000"}'
    fake = Fake([bad, ACT_CALC, FINAL])
    res = r.run_react(fake, "?", reg)
    assert res.stopped == "answer" and res.tool_errors == 1
    assert res.steps[0].ok is False and res.steps[0].observation.startswith("ERROR")
    assert "ERROR: calculator" in fake.calls[1][-1]["content"], "lỗi tool là Observation cho lượt sau"


def test_run_format_error_then_recover(r):
    reg = Registry()
    fake = Fake(["Giá là 55.000 đồng.", FINAL])
    res = r.run_react(fake, "?", reg)
    assert res.stopped == "answer" and res.format_errors == 1
    assert [s.kind for s in res.steps] == ["format_error", "final"]
    retry = fake.calls[1]
    assert retry[-2] == {"role": "assistant", "content": "Giá là 55.000 đồng."}
    assert retry[-1]["role"] == "user" and retry[-1]["content"].startswith("Lỗi định dạng:")
    assert "Final Answer" in retry[-1]["content"], "đưa thông điệp của ReActParseError cho model"


def test_run_too_many_format_errors(r):
    fake = Fake(["không đúng định dạng"] * 10)
    res = r.run_react(fake, "?", Registry(), max_format_retries=2)
    assert res.stopped == "format_error" and res.answer is None
    assert len(fake.calls) == 3, "lỗi định dạng liên tiếp thứ max_format_retries + 1 thì dừng"
    fake = Fake(["sai", ACT_SEARCH, "sai", "sai", FINAL])
    res = r.run_react(fake, "?", Registry(), max_format_retries=2)
    assert res.stopped == "answer", "đếm lỗi LIÊN TIẾP: lượt hợp lệ ở giữa đặt lại bộ đếm"
    assert res.format_errors == 3


def test_run_step_budget(r):
    reg = Registry()
    fake = Fake([ACT_SEARCH, ACT_CALC] * 5)
    res = r.run_react(fake, "?", reg, max_steps=3)
    assert res.stopped == "max_steps" and res.answer is None
    assert len(fake.calls) == 3 and len(reg.calls) == 3


def test_run_repeated_action(r):
    reg = Registry()
    fake = Fake([ACT_SEARCH] * 6)
    res = r.run_react(fake, "?", reg, max_repeats=2)
    assert res.stopped == "repeated_action"
    assert len(reg.calls) == 2, "cùng tool, cùng tham số: thực thi tối đa max_repeats lần liên tiếp"
    assert res.steps[-1].kind == "repeat" and len(fake.calls) == 3
    same_args_other_order = 'Action: search_books\nAction Input: {"query": "Tắt đèn"}'
    reg = Registry()
    res = r.run_react(Fake([ACT_SEARCH, ACT_CALC, ACT_SEARCH, ACT_CALC, FINAL]), "?", reg, max_repeats=1)
    assert res.stopped == "answer", "xen kẽ hai action khác nhau không phải lặp liên tiếp"
    reg = Registry()
    res = r.run_react(Fake([ACT_SEARCH, same_args_other_order, FINAL]), "?", reg, max_repeats=1)
    assert res.stopped == "repeated_action" and len(reg.calls) == 1


def test_run_repeat_compares_args_not_text(r):
    reg = Registry()
    a = 'Action: calculator\nAction Input: {"expression": "1+1", "note": "x"}'
    b = 'Thought: thử lại\nAction: calculator\nAction Input: {"note": "x", "expression": "1+1"}'
    res = r.run_react(Fake([a, b, FINAL]), "?", reg, max_repeats=1)
    assert res.stopped == "repeated_action", "cùng dict tham số (khác thứ tự khoá, khác Thought) vẫn là lặp"


def test_run_llm_error_stops(r):
    class Down(Fake):
        def chat(self, messages, **kwargs):
            self.calls.append(messages)
            if len(self.calls) == 2:
                raise llmkit.LLMError("Không kết nối được Ollama")
            return ACT_SEARCH

    res = r.run_react(Down(), "?", Registry())
    assert res.stopped == "llm_error" and "Ollama" in res.error and res.answer is None
    assert [s.kind for s in res.steps] == ["action"]


def test_run_history_and_custom_system(r):
    history = [{"role": "user", "content": "Tôi tên Lan."}, {"role": "assistant", "content": "Chào Lan."}]
    snapshot = [dict(m) for m in history]
    fake = Fake([FINAL])
    res = r.run_react(fake, "Tôi tên gì?", Registry(), history=history, system="Tool:\n{tools}\nHết.")
    sent = fake.calls[0]
    assert sent[0]["content"].startswith("Tool:\n- search_books") and sent[0]["content"].endswith("Hết.")
    assert sent[1:3] == snapshot and sent[3] == {"role": "user", "content": "Tôi tên gì?"}
    assert history == snapshot
    res.messages.append({"role": "user", "content": "x"})
    assert history == snapshot, "không sửa list history của người gọi"
