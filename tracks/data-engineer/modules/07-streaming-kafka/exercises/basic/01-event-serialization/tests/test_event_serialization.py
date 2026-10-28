import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)

VALID = {
    "event_id": "e-0001",
    "order_id": "e481f51cbdc54678b7cc49136f2d6af7",
    "status": "created",
    "amount": 129.9,
    "customer_state": "SP",
    "customer_city": "são paulo",
    "event_time": "2018-01-02T10:15:00Z",
}


@pytest.fixture(scope="module")
def events():
    return ex.module("events.py")


def test_validate_ok(events):
    assert events.validate(VALID) == []


@pytest.mark.parametrize(
    "patch",
    [
        {"amount": -5},
        {"status": "lost"},
        {"order_id": ""},
        {"amount": "129.9"},
    ],
)
def test_validate_reports_errors(events, patch):
    bad = {**VALID, **patch}
    errors = events.validate(bad)
    assert isinstance(errors, list) and len(errors) >= 1
    assert all(isinstance(e, str) for e in errors)


def test_validate_missing_required(events):
    bad = {k: v for k, v in VALID.items() if k != "event_time"}
    assert any("event_time" in e for e in events.validate(bad))


def test_serialize_compact_sorted_utf8(events):
    data = events.serialize(VALID)
    assert isinstance(data, bytes)
    text = data.decode("utf-8")
    assert " " not in text.replace("são paulo", "")
    assert "são paulo" in text, "Giữ nguyên ký tự Unicode (ensure_ascii=False)"
    assert list(json.loads(text).keys()) == sorted(VALID.keys())


def test_serialize_rejects_invalid(events):
    with pytest.raises(ValueError):
        events.serialize({**VALID, "amount": -1})


def test_roundtrip(events):
    assert events.deserialize(events.serialize(VALID)) == VALID


@pytest.mark.parametrize("raw", [b"not json", b"[1, 2]", b"\xff\xfe"])
def test_deserialize_bad_input(events, raw):
    with pytest.raises(ValueError):
        events.deserialize(raw)


def test_message_key(events):
    assert events.message_key(VALID) == b"e481f51cbdc54678b7cc49136f2d6af7"
    with pytest.raises(ValueError):
        events.message_key({"event_id": "x"})
