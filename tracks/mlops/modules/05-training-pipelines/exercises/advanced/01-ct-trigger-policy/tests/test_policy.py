import re
from pathlib import Path

import yaml

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
VALID = {"retrain", "skip", "investigate"}
EXPECTED = {
    "C1": ("skip", ["MAE"]),
    "C2": ("skip", ["PSI"]),
    "C3": ("retrain", ["SLO"]),
    "C4": ("investigate", ["null"]),
    "C5": ("retrain", ["tuổi"]),
    "C6": ("skip", ["nhãn"]),
    "C7": ("investigate", ["cooldown"]),
}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text: str) -> list[str]:
    return re.findall(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)


def decision_problems(data: dict) -> list[str]:
    found = []
    for key, (decision, words) in EXPECTED.items():
        entry = data.get(key)
        if not isinstance(entry, dict):
            found.append(f"{key}: thiếu mục")
            continue
        if entry.get("decision") not in VALID:
            found.append(f"{key}: decision phải là một trong {sorted(VALID)}")
        elif entry["decision"] != decision:
            found.append(f"{key}: quyết định '{entry['decision']}' không khớp chính sách")
        reasons = entry.get("reasons")
        if not isinstance(reasons, list) or not reasons or not all(isinstance(r, str) and len(r) >= 10 and r != "TODO" for r in reasons):
            found.append(f"{key}: reasons cần ít nhất một lý do dài từ 10 ký tự")
            continue
        text = " ".join(reasons).lower()
        for word in words:
            if word.lower() not in text:
                found.append(f"{key}: lý do phải nhắc '{word}'")
    return found


def policy_problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for number in range(1, 6):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 2), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 4:
        found.append("Phần 2: cần khối mermaid có ít nhất 4 cạnh")
    rows = [r for r in table_rows(section(doc, 3)) if len(r) >= 3 and all(r[:3])]
    if len(rows) < 4:
        found.append("Phần 3: bảng ít nhất 4 trigger đủ 3 cột")
    guard = " ".join(bullets(section(doc, 4))).lower()
    if len(bullets(section(doc, 4))) < 3:
        found.append("Phần 4: ít nhất 3 gạch đầu dòng")
    for word in ("cooldown", "nhãn"):
        if word not in guard:
            found.append(f"Phần 4: guardrail phải nhắc '{word}'")
    if len(bullets(section(doc, 5))) < 3:
        found.append("Phần 5: ít nhất 3 gạch đầu dòng")
    return found


def test_scenarios_fixture_present():
    data = yaml.safe_load((FIXTURES / "scenarios.yaml").read_text(encoding="utf-8"))
    assert set(data["scenarios"]) == set(EXPECTED)


def test_decisions_follow_the_stated_policy():
    data = yaml.safe_load(ex.read("decisions.yaml")) or {}
    problems = decision_problems(data)
    assert not problems, "\n".join(problems)


def test_policy_document_has_required_structure():
    problems = policy_problems(ex.read("POLICY.md"))
    assert not problems, "\n".join(problems)


def test_checker_catches_blind_retrain_and_empty_reasons():
    blind = {k: {"decision": "retrain", "reasons": ["một lý do đủ dài ở đây"]} for k in EXPECTED}
    assert any("C1" in p for p in decision_problems(blind))
    assert any("C4" in p for p in decision_problems(blind))
    assert any("C1" in p for p in decision_problems({"C1": {"decision": "skip", "reasons": []}}))
    assert policy_problems("# x\n\nTODO\n")
