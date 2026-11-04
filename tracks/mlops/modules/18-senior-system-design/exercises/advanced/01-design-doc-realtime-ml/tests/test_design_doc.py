import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"


def section(doc, number):
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table(text):
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        return [], []
    return [c.lower() for c in rows[0]], rows[2:]


def bullets(text):
    return re.findall(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)


def prose(text):
    kept, fenced = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.strip() and not line.strip().startswith("|"):
            kept.append(line)
    return "\n".join(kept).strip()


def problems(doc):
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for n in range(1, 9):
        if not re.search(rf"^## {n}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {n}.'")
    if not re.search(r"^Đề:\s*(fraud|eta)\s*$", doc, re.M | re.I):
        found.append("Dòng 'Đề: fraud' hoặc 'Đề: eta' ngay dưới tiêu đề")

    s1 = section(doc, 1)
    header, rows = table(s1)
    if header[:2] != ["yêu cầu", "con số"]:
        found.append("Phần 1: bảng cần cột Yêu cầu, Con số")
    if len([r for r in rows if len(r) >= 2 and re.search(r"\d", r[1])]) < 5:
        found.append("Phần 1: ít nhất 5 yêu cầu có con số")
    if "ngoài phạm vi" not in s1.lower() or len(bullets(s1)) < 2:
        found.append("Phần 1: nêu ngoài phạm vi với ít nhất 2 gạch đầu dòng")

    header, rows = table(section(doc, 2))
    if header[:4] != ["sli", "đo ở đâu", "slo", "cửa sổ"]:
        found.append("Phần 2: bảng cần cột SLI, Đo ở đâu, SLO, Cửa sổ")
    rows = [r for r in rows if len(r) >= 4]
    if len(rows) < 4 or any(not all(r[:4]) for r in rows):
        found.append("Phần 2: ít nhất 4 SLI, không ô trống")
    names = " ".join(r[0].lower() for r in rows)
    if "chất lượng" not in names or not re.search(r"freshness|độ tươi", names):
        found.append("Phần 2: phải có SLI chất lượng và SLI freshness")

    s3 = section(doc, 3)
    diagram = re.search(r"```mermaid\n(.*?)```", s3, re.S)
    if not diagram or len(re.findall(r"-->|-\.->|==>", diagram.group(1))) < 8:
        found.append("Phần 3: cần khối mermaid có ít nhất 8 cạnh")
    if len(prose(s3)) < 200:
        found.append("Phần 3: cần ít nhất 200 ký tự giải thích ngoài sơ đồ")

    header, rows = table(section(doc, 4))
    if header[:5] != ["phương án", "chi phí", "độ trễ", "chất lượng", "chọn"]:
        found.append("Phần 4: bảng cần cột Phương án, Chi phí, Độ trễ, Chất lượng, Chọn")
    rows = [r for r in rows if len(r) >= 5]
    if len(rows) < 3:
        found.append("Phần 4: ít nhất 3 phương án")
    if sum(1 for r in rows if r[4].lower() == "có") != 1:
        found.append("Phần 4: đúng một phương án có cột Chọn là 'có'")

    estimates = bullets(section(doc, 5))
    if len([b for b in estimates if re.search(r"\d", b)]) < 3:
        found.append("Phần 5: ít nhất 3 gạch đầu dòng ước tính có con số")

    s6 = section(doc, 6)
    header, rows = table(s6)
    if header[:3] != ["hỏng", "phát hiện", "giảm thiểu"]:
        found.append("Phần 6: bảng cần cột Hỏng, Phát hiện, Giảm thiểu")
    rows = [r for r in rows if len(r) >= 3]
    if len(rows) < 5 or any(not all(r[:3]) for r in rows):
        found.append("Phần 6: ít nhất 5 chế độ hỏng, không ô trống")
    if "fallback" not in s6.lower():
        found.append("Phần 6: phải có fallback")

    s7 = section(doc, 7).lower()
    if len(bullets(s7)) < 3 or not re.search(r"shadow|canary", s7) or "rollback" not in s7:
        found.append("Phần 7: ít nhất 3 gạch đầu dòng, có shadow hoặc canary, và rollback")

    questions = [b for b in bullets(section(doc, 8)) if b.strip().endswith("?")]
    if len(questions) < 6:
        found.append("Phần 8: ít nhất 6 câu hỏi review kết thúc bằng '?'")
    return found


def test_design_doc_has_required_structure():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_weak_design():
    found = problems((FIXTURES / "DESIGN.bad.md").read_text(encoding="utf-8"))
    assert len(found) >= 8
    assert any("freshness" in f for f in found)
    assert any("Chọn" in f for f in found)
    assert any("fallback" in f for f in found)
