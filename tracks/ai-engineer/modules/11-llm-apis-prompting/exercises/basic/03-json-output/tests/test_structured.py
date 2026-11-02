import copy
import itertools
import json

import jsonschema
import pytest

from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)

SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {"type": "string", "enum": ["negative", "neutral", "positive"]},
        "topic": {"type": "string", "enum": ["lecturer", "training_program", "facility", "others"]},
        "aspects": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 40}, "maxItems": 3},
        "severity": {"type": "integer", "minimum": 1, "maximum": 5},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "actionable": {"type": "boolean"},
        "suggestion": {"type": ["string", "null"]},
    },
    "required": ["sentiment", "topic", "actionable"],
    "additionalProperties": False,
}
GOOD = {"sentiment": "negative", "topic": "facility", "aspects": ["máy lạnh", "phòng học"], "severity": 3,
        "confidence": 0.8, "actionable": True, "suggestion": "sửa máy lạnh"}


@pytest.fixture(scope="module")
def s():
    return ex.module("structured.py")


# ---------- extract_json ----------

@pytest.mark.parametrize("text, expected", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"label": "positive"}\n```', {"label": "positive"}),
    ('Kết quả phân loại:\n{"label": "neutral", "note": "có {ngoặc} trong chuỗi"}\nHết.', {"label": "neutral", "note": "có {ngoặc} trong chuỗi"}),
    ('Dạng {label: positive} sai, đúng là {"label": "positive"}', {"label": "positive"}),
    ('[1, 2, {"x": [3]}] và thêm {"y": 1}', [1, 2, {"x": [3]}]),
    ('  {"outer": {"inner": [1, {"deep": true}]}}  ', {"outer": {"inner": [1, {"deep": True}]}}),
])
def test_extract_json(s, text, expected):
    assert s.extract_json(text) == expected


@pytest.mark.parametrize("text", ["positive", "", '{"label": "positive"', "nhãn là {tích cực}"])
def test_extract_json_raises(s, text):
    with pytest.raises(ValueError):
        s.extract_json(text)


# ---------- validate ----------

def test_validate_good(s):
    assert s.validate(GOOD, SCHEMA) == []
    assert s.validate({"sentiment": "neutral", "topic": "others", "actionable": False, "suggestion": None}, SCHEMA) == []


@pytest.mark.parametrize("patch, path", [
    ({"sentiment": "tích cực"}, "$.sentiment"),
    ({"topic": 2}, "$.topic"),
    ({"aspects": ["ok", ""]}, "$.aspects[1]"),
    ({"aspects": ["x" * 41]}, "$.aspects[0]"),
    ({"aspects": ["a", "b", "c", "d"]}, "$.aspects"),
    ({"severity": 7}, "$.severity"),
    ({"severity": 2.5}, "$.severity"),
    ({"severity": True}, "$.severity"),
    ({"confidence": -0.1}, "$.confidence"),
    ({"confidence": "0.9"}, "$.confidence"),
    ({"actionable": "yes"}, "$.actionable"),
    ({"suggestion": 5}, "$.suggestion"),
    ({"extra": 1}, "$"),
])
def test_validate_reports_path(s, patch, path):
    errors = s.validate({**GOOD, **patch}, SCHEMA)
    assert errors, f"{patch} phải bị bắt"
    assert any(e.split(":")[0] == path for e in errors), f"lỗi phải bắt đầu bằng đường dẫn {path!r}: {errors}"


def test_validate_missing_required_and_not_object(s):
    errors = s.validate({"sentiment": "neutral"}, SCHEMA)
    assert len([e for e in errors if e.startswith("$:")]) == 2, "thiếu topic và actionable: hai lỗi ở $"
    assert any("topic" in e for e in errors) and any("actionable" in e for e in errors)
    assert s.validate(["không phải object"], SCHEMA)
    assert s.validate(None, SCHEMA)


def test_validate_number_accepts_int_but_not_bool(s):
    assert s.validate(1, {"type": "number"}) == []
    assert s.validate(1.0, {"type": "integer"}) != [], "1.0 không phải integer trong tập con của bài"
    assert s.validate(False, {"type": "integer"}) != []
    assert s.validate(False, {"type": "number"}) != []


def _variants():
    values = {
        "sentiment": ["negative", "neu", None],
        "topic": ["lecturer", 3],
        "aspects": [[], ["a"], ["a", "b", "c", "d"], [""], "a"],
        "severity": [1, 5, 0, 6, 2.0, True],
        "actionable": [True, 0],
    }
    keys = list(values)
    for combo in itertools.islice(itertools.product(*values.values()), 0, None, 7):
        yield dict(zip(keys, combo))


def test_validate_agrees_with_jsonschema(s):
    checked = 0
    for case in _variants():
        for drop in (None, "topic"):
            inst = {k: v for k, v in case.items() if k != drop}
            ours = s.validate(inst, SCHEMA) == []
            ref = jsonschema.Draft202012Validator(SCHEMA).is_valid(inst)
            if isinstance(inst.get("severity"), float) and inst["severity"].is_integer():
                continue   # jsonschema coi 2.0 là integer; tập con của bài thì không (xem README)
            assert ours == ref, f"khác jsonschema ở {inst}"
            checked += 1
    assert checked > 50


# ---------- generate_validated ----------

class SchemaLLM(FakeLLM):
    def __init__(self, replies):
        super().__init__(replies)
        self.schemas = []

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None):
        self.schemas.append(json_schema)
        return super().chat(messages, model=model, temperature=temperature, json_schema=json_schema)


MESSAGES = [{"role": "system", "content": "Trích xuất JSON."}, {"role": "user", "content": "Phòng học nóng quá."}]


def test_generate_first_try(s):
    llm = SchemaLLM([json.dumps(GOOD, ensure_ascii=False)])
    assert s.generate_validated(llm, MESSAGES, SCHEMA) == GOOD
    assert len(llm.calls) == 1 and llm.schemas == [SCHEMA], "truyền json_schema=schema cho mọi lời gọi"
    assert llm.calls[0] == MESSAGES


def test_generate_retries_with_feedback(s):
    bad = {**GOOD, "sentiment": "tiêu cực"}
    replies = ["Đây là kết quả: " + json.dumps(bad, ensure_ascii=False), "```json\n" + json.dumps(GOOD) + "\n```"]
    llm = SchemaLLM(replies)
    before = copy.deepcopy(MESSAGES)
    assert s.generate_validated(llm, MESSAGES, SCHEMA, max_retries=2) == GOOD
    assert MESSAGES == before, "không sửa messages đầu vào"
    assert len(llm.calls) == 2
    second = llm.calls[1]
    assert second[:2] == MESSAGES
    assert second[2] == {"role": "assistant", "content": replies[0]}, "câu trả lời sai được đưa lại vào lịch sử"
    assert second[3]["role"] == "user" and "$.sentiment" in second[3]["content"], "feedback nêu đường dẫn lỗi"


def test_generate_gives_up(s):
    llm = SchemaLLM(["không có JSON", '{"sentiment": "neutral"}', "{hỏng"])
    with pytest.raises(s.ExtractionError) as info:
        s.generate_validated(llm, MESSAGES, SCHEMA, max_retries=2)
    assert len(llm.calls) == 3, "max_retries=2 nghĩa là tối đa 3 lần gọi"
    attempts = info.value.attempts
    assert [a["reply"] for a in attempts] == ["không có JSON", '{"sentiment": "neutral"}', "{hỏng"]
    assert all(a["errors"] for a in attempts)
    assert any("topic" in e for e in attempts[1]["errors"])


def test_generate_zero_retries(s):
    llm = SchemaLLM(["sai"])
    with pytest.raises(s.ExtractionError):
        s.generate_validated(llm, MESSAGES, SCHEMA, max_retries=0)
    assert len(llm.calls) == 1
