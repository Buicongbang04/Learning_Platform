import re

import pandas as pd
import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
TYPES = {"string", "integer", "number", "boolean", "timestamp", "array"}
PII = {"email", "phone", "phone_number", "full_name", "name", "address"}
PLAN_HEADINGS = ["## Câu hỏi và metric", "## Sự kiện", "## Phân tích phân khúc", "## QA trước khi ra mắt",
                 "## Rủi ro và quyền riêng tư"]

PLAN = {
    "feature": "Khối gợi ý thử nghiệm",
    "common_properties": {
        "anonymous_id": {"type": "string", "required": True},
        "event_time": {"type": "timestamp", "required": True},
        "user_id": {"type": "string", "required": False},
    },
    "events": {
        "recommendation_shown": {
            "trigger": "Khi khối gợi ý hiện trong viewport", "owner": "team-x", "metrics": ["ctr"],
            "properties": {
                "item_id": {"type": "string", "required": True},
                "position": {"type": "integer", "required": True},
                "source": {"type": "string", "required": True, "enum": ["basket_rules", "bestseller"]},
                "price": {"type": "number", "required": False},
                "in_stock": {"type": "boolean", "required": False},
                "item_ids": {"type": "array", "required": False},
            },
        },
        "recommendation_clicked": {
            "trigger": "Khi bấm vào một sản phẩm gợi ý", "owner": "team-x", "metrics": ["ctr"],
            "properties": {"item_id": {"type": "string", "required": True}},
        },
    },
}


def shown(**changes):
    props = {"anonymous_id": "a1", "event_time": "2026-10-30T10:00:00Z", "item_id": "22697", "position": 1,
             "source": "basket_rules", "price": 2.95, "in_stock": True, "item_ids": ["22697", "22698"]}
    props.update(changes)
    return {"event": "recommendation_shown", "properties": {k: v for k, v in props.items() if v is not ...}}


@pytest.fixture(scope="module")
def validator():
    return ex.module("validate_events.py")


def test_valid_event_has_no_issue(validator):
    assert validator.validate_event(shown(), PLAN) == []
    assert validator.validate_event(shown(user_id=None, price=..., in_stock=...), PLAN) == [], "Thuộc tính tuỳ chọn được thiếu"
    assert validator.validate_event(shown(price=3), PLAN) == [], "number nhận cả số nguyên"
    assert validator.validate_event(shown(event_time="2026-10-30T10:00:00+07:00"), PLAN) == []


def test_unknown_event(validator):
    event = {"event": "RecommendationShown", "properties": shown()["properties"]}
    assert validator.validate_event(event, PLAN) == ["unknown_event"]


def test_missing_required(validator):
    assert validator.validate_event(shown(item_id=...), PLAN) == ["missing:item_id"]
    assert validator.validate_event(shown(item_id=None), PLAN) == ["missing:item_id"], "None coi là thiếu"
    assert validator.validate_event(shown(anonymous_id=...), PLAN) == ["missing:anonymous_id"], "Thuộc tính chung cũng bắt buộc"


def test_wrong_types(validator):
    event = shown(position="1", price=True, in_stock=1, event_time="hôm qua", item_id=22697, item_ids="22697")
    assert validator.validate_event(event, PLAN) == sorted([
        "type:event_time", "type:in_stock", "type:item_id", "type:item_ids", "type:position", "type:price"])
    assert validator.validate_event(shown(position=1.0), PLAN) == ["type:position"], "integer không nhận số thực"
    assert validator.validate_event(shown(position=True), PLAN) == ["type:position"], "bool không phải integer"


def test_enum_and_extra(validator):
    assert validator.validate_event(shown(source="Search"), PLAN) == ["enum:source"]
    assert validator.validate_event(shown(email="a@b.c", source="search"), PLAN) == ["enum:source", "extra:email"]


def test_validate_log(validator):
    events = [shown(), shown(source="Search"), shown(source="search"), shown(item_id=...),
              {"event": "page_view", "properties": {}}, {"event": "recommendation_clicked",
                                                         "properties": {"anonymous_id": "a", "event_time": "2026-10-30"}}]
    out = validator.validate_log(events, PLAN)
    assert list(out.columns) == ["event", "issue", "count"]
    assert out.values.tolist() == [
        ["recommendation_shown", "enum:source", 2],
        ["page_view", "unknown_event", 1],
        ["recommendation_clicked", "missing:item_id", 1],
        ["recommendation_shown", "missing:item_id", 1],
    ]
    empty = validator.validate_log([shown()], PLAN)
    assert empty.empty and list(empty.columns) == ["event", "issue", "count"]


SAMPLE = {"string": "x", "integer": 1, "number": 1.5, "boolean": True, "timestamp": "2026-10-30T10:00:00Z",
          "array": ["x"]}


@pytest.fixture(scope="module")
def plan():
    try:
        data = yaml.safe_load(ex.read("tracking_plan.yaml"))
    except yaml.YAMLError as exc:  # để test báo FAIL có lý do, không ERROR ở fixture
        return f"YAML lỗi: {exc}"
    return data if isinstance(data, dict) else "tracking_plan.yaml phải là mapping (feature, common_properties, events)"


def test_plan_file(plan):
    assert "TODO" not in ex.read("tracking_plan.yaml"), "Còn TODO trong tracking_plan.yaml"
    assert isinstance(plan, dict), plan


def all_properties(plan):
    for name, spec in (plan.get("common_properties") or {}).items():
        yield "common", name, spec
    for event, espec in plan["events"].items():
        for name, spec in (espec.get("properties") or {}).items():
            yield event, name, spec


def test_plan_structure(plan):
    assert isinstance(plan, dict), plan
    assert isinstance(plan.get("feature"), str) and plan["feature"].strip()
    common = plan.get("common_properties") or {}
    for key in ("anonymous_id", "session_id", "event_time"):
        assert key in common and common[key].get("required") is True, f"Thiếu thuộc tính chung bắt buộc {key}"
    assert "user_id" in common, "Cần user_id (tuỳ chọn) để nối hành vi trước và sau đăng nhập"
    events = plan.get("events") or {}
    assert len(events) >= 4, "Ít nhất 4 sự kiện"
    assert sum(name.startswith("recommendation_") for name in events) >= 2, "Ít nhất 2 sự kiện của khối gợi ý"
    for name, spec in events.items():
        assert re.fullmatch(r"[a-z]+(_[a-z]+)+", name), f"{name}: tên snake_case dạng object_action"
        for key in ("trigger", "owner"):
            assert isinstance(spec.get(key), str) and spec[key].strip(), f"{name}: thiếu {key}"
        assert isinstance(spec.get("metrics"), list) and spec["metrics"], f"{name}: sự kiện phải phục vụ ít nhất 1 metric"
        assert isinstance(spec.get("properties"), dict) and spec["properties"], f"{name}: thiếu properties"


def test_plan_properties(plan):
    assert isinstance(plan, dict), plan
    enums = 0
    for where, name, spec in all_properties(plan):
        assert isinstance(spec, dict), f"{where}.{name}: cần type và required"
        assert spec.get("type") in TYPES, f"{where}.{name}: type phải thuộc {sorted(TYPES)}"
        assert isinstance(spec.get("required"), bool), f"{where}.{name}: required là true/false"
        assert name not in PII, f"{where}.{name}: không đưa dữ liệu cá nhân vào sự kiện"
        if "enum" in spec:
            assert isinstance(spec["enum"], list) and spec["enum"], f"{where}.{name}: enum là danh sách không rỗng"
            enums += 1
    assert enums >= 1, "Có ít nhất một thuộc tính enum (vd. nguồn của gợi ý)"


def test_plan_accepts_its_own_sample_events(plan, validator):
    assert isinstance(plan, dict), plan
    for event, espec in plan["events"].items():
        props = {}
        for _, name, spec in all_properties({"common_properties": plan.get("common_properties"), "events": {event: espec}}):
            if spec.get("required"):
                props[name] = spec["enum"][0] if spec.get("enum") else SAMPLE[spec["type"]]
        assert validator.validate_event({"event": event, "properties": props}, plan) == [], event


def test_plan_doc():
    doc = ex.read("PLAN.md")
    assert "TODO" not in doc, "Còn dòng TODO trong PLAN.md"
    words = len(doc.split())
    assert 250 <= words <= 900, f"PLAN.md 250-900 từ, hiện có {words}"
    for heading in PLAN_HEADINGS:
        assert heading in doc, f"Thiếu mục {heading}"
