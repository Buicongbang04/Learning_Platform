import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
TEMPLATE = Path(__file__).parent / "fixtures" / "DECISION.template.md"
REQUIRED_OPTIONS = {"monorepo": re.compile(r"mono", re.I), "polyrepo": re.compile(r"poly|multi", re.I)}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def list_items(text: str, numbered: bool = False) -> list[str]:
    marker = r"\d+\." if numbered else r"(?:\d+\.|-)"
    return [m.group(1).strip() for m in re.finditer(rf"^\s*{marker}\s+(.+)$", text, re.M)]


def problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    if len(section(doc, 1).strip()) < 250:
        found.append("Phần 1: bối cảnh cần ít nhất 250 ký tự")
    rows = [r for r in table_rows(section(doc, 2)) if len(r) >= 6 and all(r[:6])]
    if len(rows) < 3:
        found.append("Phần 2: ít nhất 3 phương án, đủ 6 cột")
    names = [r[0] for r in rows]
    missing = [name for name, pattern in REQUIRED_OPTIONS.items() if not any(pattern.search(n) for n in names)]
    if missing:
        found.append(f"Phần 2: bảng phải có {missing}")
    bad_scores = [r[0] for r in rows if not (r[5].isdigit() and 1 <= int(r[5]) <= 5)]
    if bad_scores:
        found.append(f"Phần 2: điểm phải là số nguyên 1–5: {bad_scores}")
    decision = section(doc, 3)
    match = re.search(r"^Chọn:\s*(.+)$", decision, re.M)
    if not match:
        found.append("Phần 3: cần dòng 'Chọn: <phương án>'")
    elif not any(n and n.lower() in match.group(1).lower() for n in names):
        found.append("Phần 3: phương án được chọn phải nằm trong bảng")
    if len(decision.strip()) < 300:
        found.append("Phần 3: lý do cần ít nhất 300 ký tự")
    if len(list_items(section(doc, 4))) < 3:
        found.append("Phần 4: ít nhất 3 gạch đầu dòng")
    if len(list_items(section(doc, 5), numbered=True)) < 4:
        found.append("Phần 5: kế hoạch ít nhất 4 bước đánh số")
    if len(list_items(section(doc, 6))) < 3:
        found.append("Phần 6: ít nhất 3 rủi ro")
    if len(list_items(section(doc, 7))) < 2:
        found.append("Phần 7: ít nhất 2 tín hiệu xem lại")
    return found


def test_decision_document():
    found = problems(ex.read("DECISION.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems(TEMPLATE.read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert any(p.startswith("Phần 2: bảng phải có") for p in found)
    assert any(p.startswith("Phần 5") for p in found)

