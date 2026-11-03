import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
PROMOTE_WORDS = re.compile(r"champion|promote|production", re.I)


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text: str) -> list[str]:
    return re.findall(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)


def prose(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        elif not fenced and not line.strip().startswith("|"):
            kept.append(line)
    return "\n".join(kept).strip()


def problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for number in range(1, 7):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 2), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 6:
        found.append("Phần 2: cần khối mermaid có ít nhất 6 cạnh")
    rows = [r for r in table_rows(section(doc, 3)) if len(r) >= 3 and all(r[:3])]
    if len(rows) < 6:
        found.append("Phần 3: bảng ít nhất 6 dòng đủ 3 cột")
    roles = [r for r in table_rows(section(doc, 4)) if len(r) >= 4 and all(r[:4])]
    if len(roles) < 5:
        found.append("Phần 4: bảng ít nhất 5 vai trò đủ 4 cột")
    for role, allowed, *_ in roles:
        if re.search(r"data scientist|\bds\b|ml engineer", role, re.I) and PROMOTE_WORDS.search(allowed):
            found.append(f"Phần 4: vai trò '{role}' không được có quyền champion/promote/production trong cột 'Được làm'")
    ops = section(doc, 5).lower()
    if len(bullets(ops)) < 4:
        found.append("Phần 5: ít nhất 4 gạch đầu dòng")
    for word in ("backup", "retention"):
        if word not in ops:
            found.append(f"Phần 5: phải nhắc '{word}'")
    if len(bullets(section(doc, 6))) < 3:
        found.append("Phần 6: ít nhất 3 gạch đầu dòng")
    return found


def test_design_has_required_structure():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_weak_design():
    found = problems((FIXTURES / "DESIGN.bad.md").read_text(encoding="utf-8"))
    assert len(found) >= 6
    assert any("Data Scientist" in f for f in found)
