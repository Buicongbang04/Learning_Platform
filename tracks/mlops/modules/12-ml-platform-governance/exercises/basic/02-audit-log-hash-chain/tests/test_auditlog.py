import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)
GENESIS = "0" * 64


@pytest.fixture
def mod():
    return ex.module("auditlog.py")


@pytest.fixture
def log(mod, tmp_path):
    return mod.AuditLog(tmp_path / "audit.jsonl")


def fill(log):
    log.append("an", "set_alias", "taxi-eta", "champion", None, 1, "model đầu tiên qua cổng", at="2026-03-01T09:00:00+00:00")
    log.append("binh", "set_alias", "taxi-eta", "challenger", None, 2, "thử nghiệm v2", at="2026-03-02T09:00:00+00:00")
    log.append("chi", "set_alias", "taxi-eta", "champion", 1, 3, "MAE giảm 4% trên 7 ngày", at="2026-03-03T09:00:00+00:00")
    log.append("an", "set_alias", "taxi-eta", "champion", 3, 1, "rollback do latency tăng", at="2026-03-04T09:00:00+00:00")
    log.append("dung", "set_alias", "fare", "champion", None, 3, "mô hình giá cước", at="2026-03-05T09:00:00+00:00")


def rewrite(log, edit):
    lines = log.path.read_text(encoding="utf-8").splitlines()
    edit(lines)
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_records_have_chain_fields(log):
    fill(log)
    entries = log.entries()
    assert [e["seq"] for e in entries] == [0, 1, 2, 3, 4]
    assert entries[0]["prev_hash"] == GENESIS
    assert all(entries[i]["prev_hash"] == entries[i - 1]["hash"] for i in range(1, 5))
    assert len({e["hash"] for e in entries}) == 5
    assert log.head() == entries[-1]["hash"]
    assert entries[2]["from_version"] == 1 and entries[2]["to_version"] == 3 and entries[0]["from_version"] is None


def test_hash_is_sha256_of_canonical_json_without_hash(log):
    import hashlib

    record = log.append("an", "set_alias", "m", "champion", None, 1, "lý do rõ ràng", at="2026-01-01T00:00:00+00:00")
    body = {k: v for k, v in record.items() if k != "hash"}
    expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert record["hash"] == expected


def test_empty_log_is_valid(log):
    assert log.entries() == []
    assert log.head() == GENESIS
    assert log.verify() is None


def test_intact_log_verifies(log):
    fill(log)
    assert log.verify() is None
    assert log.verify(anchor=log.head()) is None


@pytest.mark.parametrize("actor,reason", [("", "lý do"), ("  ", "lý do"), ("an", ""), ("an", "   ")])
def test_rejects_blank_actor_or_reason_without_writing(log, actor, reason):
    with pytest.raises(ValueError):
        log.append(actor, "set_alias", "m", "champion", None, 1, reason)
    assert log.entries() == []


def test_append_only_never_rewrites_existing_bytes(log):
    log.append("an", "set_alias", "m", "champion", None, 1, "một", at="2026-01-01T00:00:00+00:00")
    before = log.path.read_bytes()
    log.append("an", "set_alias", "m", "champion", 1, 2, "hai", at="2026-01-02T00:00:00+00:00")
    after = log.path.read_bytes()
    assert after.startswith(before) and len(after) > len(before)


def test_two_instances_continue_the_same_chain(mod, tmp_path):
    path = tmp_path / "shared.jsonl"
    first, second = mod.AuditLog(path), mod.AuditLog(path)
    first.append("an", "set_alias", "m", "champion", None, 1, "một", at="2026-01-01T00:00:00+00:00")
    second.append("binh", "set_alias", "m", "champion", 1, 2, "hai", at="2026-01-02T00:00:00+00:00")
    first.append("chi", "set_alias", "m", "champion", 2, 3, "ba", at="2026-01-03T00:00:00+00:00")
    assert [e["seq"] for e in first.entries()] == [0, 1, 2]
    assert first.verify() is None


def test_editing_a_reason_is_detected_at_that_entry(log):
    fill(log)
    rewrite(log, lambda lines: lines.__setitem__(2, lines[2].replace("MAE giảm 4%", "MAE giảm 40%")))
    assert log.verify() == 2


def test_deleting_a_middle_entry_is_detected(log):
    fill(log)
    rewrite(log, lambda lines: lines.pop(1))
    assert log.verify() == 1


def test_swapping_two_entries_is_detected(log):
    fill(log)
    rewrite(log, lambda lines: lines.__setitem__(slice(1, 3), [lines[2], lines[1]]))
    assert log.verify() == 1


def test_fixing_the_hash_of_an_edited_entry_breaks_the_next_link(log):
    import hashlib

    fill(log)
    forged = {**log.entries()[1], "actor": "mallory"}
    body = {k: v for k, v in forged.items() if k != "hash"}
    forged["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    rewrite(log, lambda lines: lines.__setitem__(1, json.dumps(forged, ensure_ascii=False)))
    assert log.verify() == 2


@pytest.mark.parametrize("damage", [
    lambda line: line[: len(line) // 2],
    lambda line: "không phải json",
    lambda line: "42",
    lambda line: "[]",
])
def test_corrupted_line_is_reported_not_raised(log, damage):
    fill(log)
    rewrite(log, lambda lines: lines.__setitem__(3, damage(lines[3])))
    assert log.verify() == 3


def test_truncation_needs_an_anchor(log):
    fill(log)
    anchor = log.head()
    rewrite(log, lambda lines: lines.__delitem__(slice(3, None)))
    assert log.verify() is None
    assert log.verify(anchor=anchor) == 3


def test_who_promoted_v3(log):
    fill(log)
    found = log.who_promoted("taxi-eta", 3)
    assert [(e["actor"], e["at"], e["reason"], e["from_version"]) for e in found] == [
        ("chi", "2026-03-03T09:00:00+00:00", "MAE giảm 4% trên 7 ngày", 1)
    ]


def test_who_promoted_ignores_other_aliases_and_models_and_keeps_order(log):
    fill(log)
    assert [e["actor"] for e in log.who_promoted("taxi-eta", 1)] == ["an", "an"]
    assert log.who_promoted("taxi-eta", 2) == []
    assert [e["actor"] for e in log.who_promoted("fare", 3)] == ["dung"]
    assert log.who_promoted("taxi-eta", 9) == []
