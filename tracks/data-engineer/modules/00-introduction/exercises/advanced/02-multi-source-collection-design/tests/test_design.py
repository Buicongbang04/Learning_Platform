import re

import yaml

from testkit import Exercise

ex = Exercise(__file__)
TYPES = {"database", "api", "log", "mobile", "iot"}
REQUIRED = ["name", "type", "direction", "mode", "frequency", "incremental_key", "dedup_key", "late_data_window",
            "raw_path", "pii", "quality_checks", "source_limits", "owner"]


def load_sources():
    text = ex.read("sources.yaml")
    assert "TODO" not in text, "Điền hết TODO trong sources.yaml"
    return yaml.safe_load(text)["sources"]


def test_covers_every_source_type():
    sources = load_sources()
    assert {s["type"] for s in sources} >= TYPES
    names = [s["name"] for s in sources]
    assert len(names) == len(set(names))


def test_every_source_has_a_complete_contract():
    sources = load_sources()
    for s in sources:
        missing = [k for k in REQUIRED if k not in s]
        assert not missing, f"{s.get('name')}: thiếu {missing}"
        assert s["type"] in TYPES
        assert s["direction"] in {"pull", "push"}
        assert s["mode"] in {"full", "incremental", "cdc", "stream"}
        assert s["frequency"] in {"realtime", "minutely", "hourly", "daily", "weekly"}
        assert re.fullmatch(r"\d+[mhd]", str(s["late_data_window"])), f"{s['name']}: late_data_window dạng 15m, 2h, 7d"
        assert len(s["quality_checks"]) >= 2, f"{s['name']}: cần ít nhất 2 quality check"
        assert s["source_limits"] and s["owner"]


def test_incremental_sources_name_their_key():
    sources = load_sources()
    for s in sources:
        if s["mode"] in {"incremental", "cdc"}:
            assert s["incremental_key"], f"{s['name']}: mode {s['mode']} cần incremental_key"


def test_dedup_key_or_reason():
    sources = load_sources()
    for s in sources:
        assert isinstance(s["dedup_key"], list)
        if not s["dedup_key"]:
            assert s.get("dedup_note"), f"{s['name']}: không có khoá dedup thì phải giải thích ở dedup_note"


def test_raw_zone_is_separate_per_source():
    sources = load_sources()
    paths = [s["raw_path"] for s in sources]
    assert all(p.startswith(("data/raw/", "s3://")) for p in paths)
    assert len(set(paths)) == len(paths)


def test_personal_data_is_declared():
    sources = load_sources()
    for s in sources:
        assert isinstance(s["pii"], list)
        if s["type"] in {"database", "mobile"}:
            assert s["pii"], f"{s['name']}: nguồn {s['type']} của khách hàng gần như chắc chắn có PII"


def test_push_sources_are_not_full_reloads():
    sources = load_sources()
    for s in sources:
        if s["direction"] == "push":
            assert s["mode"] != "full", f"{s['name']}: nguồn push không 'tải lại toàn bộ' được"


def test_design_document():
    text = ex.read("design.md")
    assert "TODO" not in text, "Điền hết TODO trong design.md"
    for heading in ("## Kiến trúc", "## Lịch chạy và phụ thuộc", "## Idempotency và chạy lại", "## Dữ liệu đến trễ",
                    "## Bảo mật và PII", "## Giám sát", "## Chi phí và dung lượng"):
        assert heading in text
    assert "```mermaid" in text.split("## Kiến trúc", 1)[1].split("\n## ", 1)[0]
    cost = text.split("## Chi phí và dung lượng", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"\d+(?:[.,]\d+)?\s*(?:KB|MB|GB|TB)", cost), "Ước lượng dung lượng bằng con số có đơn vị"
