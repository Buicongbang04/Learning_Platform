import yaml

from testkit import Exercise

ex = Exercise(__file__)
VALID = {"none", "feast", "managed"}
EXPECTED = {
    "S1": ("none", ["online"]),
    "S2": ("none", ["thân yêu cầu"]),
    "S3": ("feast", ["point-in-time", "online"]),
    "S4": ("managed", ["streaming", "SLA"]),
    "S5": ("none", ["parity"]),
    "S6": ("none", ["theo lô"]),
}


def problems(data: dict) -> list[str]:
    found = []
    for key, (decision, words) in EXPECTED.items():
        entry = data.get(key)
        if not isinstance(entry, dict):
            found.append(f"{key}: thiếu mục")
            continue
        if entry.get("decision") not in VALID:
            found.append(f"{key}: decision phải là một trong {sorted(VALID)}")
        elif entry["decision"] != decision:
            found.append(f"{key}: quyết định '{entry['decision']}', mong đợi theo tình huống là '{decision}'")
        reasons = entry.get("reasons")
        if not isinstance(reasons, list) or not reasons or not all(isinstance(r, str) and len(r) >= 20 and "TODO" not in r for r in reasons):
            found.append(f"{key}: reasons cần ít nhất một lý do dài từ 20 ký tự")
            continue
        text = " ".join(reasons).lower()
        for word in words:
            if word.lower() not in text:
                found.append(f"{key}: lý do phải nhắc '{word}'")
    return found


def test_decisions_match_scenarios():
    data = yaml.safe_load(ex.read("decisions.yaml")) or {}
    found = problems(data)
    assert not found, "\n".join(found)


def test_checker_rejects_reflexive_answers():
    reflex = {k: {"decision": "feast", "reasons": ["Feature store luôn tốt hơn, nên dùng ở mọi nơi có thể"]} for k in EXPECTED}
    found = problems(reflex)
    assert len(found) >= 8
    assert any(f.startswith("S1") and "none" in f for f in found)
    assert any(f.startswith("S4") and "managed" in f for f in found)
