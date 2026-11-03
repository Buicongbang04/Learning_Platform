import json

import pytest
import yaml

from testkit import ROOT, Exercise

ex = Exercise(__file__)
PILLARS = {"field", "customer", "design", "cloud"}
PILLAR_MODULES = {
    "field": {f"{n:02d}" for n in range(1, 11)},
    "customer": {f"{n:02d}" for n in range(11, 15)},
    "design": {"15", "16", "17", "18", "20"},
    "cloud": {"19", "c1", "c2", "c3"},
}
EXPECTED = {
    "r1": ("field", {"03-airgapped-proxy", "08-field-troubleshooting"}),
    "r2": ("customer", {"13-business-roi"}),
    "r3": ("field", {"09-production-trust"}),
    "r4": ("customer", {"11-discovery-requirements", "12-scoping-sequencing"}),
    "r5": ("design", {"17-system-design-core", "18-system-design-fde"}),
    "r6": ("cloud", {"19-cloud-iac", "c1-aws-byoc"}),
}
TEXT_FIELDS = ("why", "first_step")
MIN_CHARS = 30


def module_ids() -> set[str]:
    track = json.loads((ROOT / "tracks" / "fde" / "track.json").read_text(encoding="utf-8"))
    return {m["id"] for m in track["modules"]}


@pytest.fixture(scope="module")
def answers() -> dict:
    data = yaml.safe_load(ex.read("requests.yaml"))
    assert isinstance(data, dict) and isinstance(data.get("requests"), dict), "requests.yaml cần khoá 'requests' là mapping"
    return data["requests"]


def test_every_request_answered_once(answers):
    assert sorted(answers) == sorted(EXPECTED), f"Cần đúng các yêu cầu {sorted(EXPECTED)}, nhận {sorted(answers)}"


def test_fields_are_valid(answers):
    known = module_ids()
    for rid, item in answers.items():
        assert isinstance(item, dict), f"{rid}: phải là mapping"
        assert item.get("pillar") in PILLARS, f"{rid}: pillar phải thuộc {sorted(PILLARS)}, nhận {item.get('pillar')!r}"
        assert item.get("module") in known, f"{rid}: module {item.get('module')!r} không có trong tracks/fde/track.json"
        assert item["module"][:2] in PILLAR_MODULES[item["pillar"]], f"{rid}: module {item['module']} không thuộc trụ {item['pillar']}"
        for field in TEXT_FIELDS:
            text = str(item.get(field) or "").strip()
            assert len(text) >= MIN_CHARS and "TODO" not in text, f"{rid}: '{field}' cần ít nhất {MIN_CHARS} ký tự, không còn TODO"
        assert item["why"].strip() != item["first_step"].strip(), f"{rid}: 'why' và 'first_step' phải khác nhau"


def test_first_steps_are_distinct(answers):
    steps = [str(item.get("first_step", "")).strip().lower() for item in answers.values()]
    assert len(set(steps)) == len(steps), "Mỗi yêu cầu cần một bước đầu tiên riêng, không chép cùng một câu"


@pytest.mark.parametrize("rid", sorted(EXPECTED))
def test_pillar_and_module(answers, rid):
    pillar, modules = EXPECTED[rid]
    item = answers.get(rid) or {}
    assert item.get("pillar") == pillar, f"{rid}: trụ chưa đúng (đang là {item.get('pillar')!r}); đọc lại câu khách thực sự hỏi gì"
    assert item.get("module") in modules, f"{rid}: module {item.get('module')!r} chưa phải nơi track dạy việc này"
