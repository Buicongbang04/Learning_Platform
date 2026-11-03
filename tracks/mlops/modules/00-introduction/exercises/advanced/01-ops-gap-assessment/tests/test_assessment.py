import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
TEMPLATE = Path(__file__).parent / "fixtures" / "ASSESSMENT.template.md"
AREAS = {"data", "training", "versioning", "serving", "monitoring", "ci-cd", "security", "rollback"}
PRIORITIES = {"P0", "P1", "P2"}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str, columns: int) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    cells = [[c.strip() for c in row] for row in rows[2:]]
    return [r for r in cells if len(r) >= columns]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("|")).strip()


def problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for number in range(1, 6):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    summary = section(doc, 1)
    if len(prose(summary)) < 200:
        found.append("Phần 1: tóm tắt cần ít nhất 200 ký tự")
    if "google" not in summary.lower() or not re.search(r"(mức|level)\s*0\b", summary, re.I):
        found.append("Phần 1: nêu mức theo Google và kết luận hệ thống này đang ở mức 0")
    rows = table_rows(section(doc, 2), 6)
    rows = [r for r in rows if all(r[:6])]
    if len(rows) < 7:
        found.append("Phần 2: ít nhất 7 dòng đủ 6 cột")
    areas = [r[0].lower() for r in rows]
    if not set(areas) <= AREAS:
        found.append(f"Phần 2: cột Khu vực chỉ nhận {sorted(AREAS)}")
    if len(set(areas) & AREAS) < 6:
        found.append("Phần 2: phủ ít nhất 6 khu vực khác nhau")
    if any(len(r[1]) < 25 for r in rows):
        found.append("Phần 2: cột Hiện trạng cần bằng chứng cụ thể (>= 25 ký tự)")
    if sum(bool(re.search(r"\d", r[1])) for r in rows) < 3:
        found.append("Phần 2: ít nhất 3 dòng trích con số từ đề (7 tuần, 40 phút, 3 ngày...)")
    prios = [r[3].upper() for r in rows]
    if not set(prios) <= PRIORITIES:
        found.append("Phần 2: cột Ưu tiên chỉ nhận P0, P1, P2")
    p0 = [r for r in rows if r[3].upper() == "P0"]
    if not 1 <= len(p0) <= 3:
        found.append("Phần 2: có từ 1 tới 3 dòng P0 (không phải mọi thứ đều khẩn cấp)")
    roadmap = section(doc, 4)
    plan = table_rows(roadmap, 3)
    phases = " ".join(r[0] for r in plan)
    if not all(day in phases for day in ("30", "60", "90")):
        found.append("Phần 4: có dòng cho mốc 30, 60 và 90 ngày")
    if not any("30" in r[0] and len(r[1]) >= 40 for r in plan):
        found.append("Phần 4: dòng 30 ngày cần mô tả việc cụ thể (>= 40 ký tự)")
    skipped = bullets(section(doc, 3))
    if len(skipped) < 2 or sum(len(b) for b in skipped) < 150:
        found.append("Phần 3: ít nhất 2 thứ cố ý chưa làm, mỗi thứ có lý do (tổng >= 150 ký tự)")
    if len(bullets(section(doc, 5))) < 2:
        found.append("Phần 5: ít nhất 2 giả định hoặc rủi ro")
    return found


def test_assessment_document():
    found = problems(ex.read("ASSESSMENT.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems(TEMPLATE.read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert "Phần 2: ít nhất 7 dòng đủ 6 cột" in found
    assert any(p.startswith("Phần 1:") for p in found)
    assert any(p.startswith("Phần 3:") for p in found)


def test_brief_is_unchanged():
    brief = (Path(__file__).parent / "fixtures" / "project-brief.md").read_text(encoding="utf-8")
    assert "12 000 request" in brief
