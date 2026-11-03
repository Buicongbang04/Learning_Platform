import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TOOLS = ("prefect", "airflow", "kubeflow", "zenml", "metaflow")
DECISIONS = ("chọn", "loại", "theo dõi")


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
    for number in range(1, 6):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: cần ít nhất 300 ký tự")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 2), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 5:
        found.append("Phần 2: cần khối mermaid có ít nhất 5 cạnh")
    rows = [r for r in table_rows(section(doc, 3)) if len(r) >= 4 and all(r[:4])]
    names = " ".join(r[0].lower() for r in rows)
    for tool in TOOLS:
        if tool not in names:
            found.append(f"Phần 3: bảng thiếu dòng cho {tool}")
    for row in rows:
        if not any(d in row[3].lower() for d in DECISIONS):
            found.append(f"Phần 3: cột Quyết định của '{row[0]}' phải là một trong {DECISIONS}")
    if sum("chọn" in r[3].lower() and "không chọn" not in r[3].lower() for r in rows) != 1:
        found.append("Phần 3: đúng một công cụ có quyết định 'chọn'")
    ops = " ".join(bullets(section(doc, 4))).lower()
    if len(bullets(section(doc, 4))) < 4:
        found.append("Phần 4: ít nhất 4 gạch đầu dòng")
    for word in ("retry", "backfill", "idempotent"):
        if word not in ops:
            found.append(f"Phần 4: phải nhắc '{word}'")
    risks = bullets(section(doc, 5))
    if len(risks) < 3:
        found.append("Phần 5: ít nhất 3 gạch đầu dòng")
    if not any(re.search(r"\d", r) for r in risks):
        found.append("Phần 5: ít nhất một điều kiện đổi công cụ phải có con số đo được")
    return found


def test_design_has_required_structure():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_weak_design():
    found = problems((FIXTURES / "DESIGN.bad.md").read_text(encoding="utf-8"))
    for needle in ("Phần 1", "Phần 2", "kubeflow", "đúng một", "Phần 4", "con số"):
        assert any(needle in f for f in found), needle
