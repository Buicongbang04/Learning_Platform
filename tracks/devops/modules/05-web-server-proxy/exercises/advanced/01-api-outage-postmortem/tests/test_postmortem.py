import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
TEMPLATE = Path(__file__).parent / "fixtures" / "POSTMORTEM.template.md"
TYPES = {"phòng ngừa", "phát hiện", "giảm thiểu"}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("|")).strip()


def problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 200:
        found.append("Phần 1: tóm tắt cần ít nhất 200 ký tự")
    if len(re.findall(r"\d[\d.,]*", section(doc, 2))) < 4:
        found.append("Phần 2: tác động cần ít nhất 4 con số")
    timeline = [r for r in table_rows(section(doc, 3)) if len(r) >= 3 and all(r[:3])]
    times = [r[0] for r in timeline]
    if len(timeline) < 10:
        found.append("Phần 3: dòng thời gian cần ít nhất 10 dòng đủ 3 cột")
    elif not all(re.fullmatch(r"\d{2}:\d{2}", t) for t in times) or times != sorted(times):
        found.append("Phần 3: cột đầu là giờ HH:MM, tăng dần")
    cause = section(doc, 4)
    if len(prose(cause)) < 500:
        found.append("Phần 4: nguyên nhân cần ít nhất 500 ký tự")
    if len(bullets(cause)) < 4:
        found.append("Phần 4: ít nhất 4 yếu tố góp phần (gạch đầu dòng)")
    if len(prose(section(doc, 5))) < 250:
        found.append("Phần 5: phát hiện và xử lý cần ít nhất 250 ký tự")
    actions = [r for r in table_rows(section(doc, 6)) if len(r) >= 4 and all(r[:4])]
    if len(actions) < 5:
        found.append("Phần 6: ít nhất 5 việc, đủ 4 cột")
    kinds = {r[1].lower() for r in actions}
    if not kinds <= TYPES:
        found.append(f"Phần 6: cột Loại chỉ nhận {sorted(TYPES)}")
    if not {"phòng ngừa", "phát hiện"} <= kinds:
        found.append("Phần 6: cần ít nhất một việc 'phòng ngừa' và một việc 'phát hiện'")
    if any(not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[3]) for r in actions):
        found.append("Phần 6: cột Hạn dạng YYYY-MM-DD")
    if len(bullets(section(doc, 7))) < 2:
        found.append("Phần 7: ít nhất 2 bài học")
    return found


def test_postmortem_document():
    found = problems(ex.read("POSTMORTEM.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems(TEMPLATE.read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert "Phần 3: dòng thời gian cần ít nhất 10 dòng đủ 3 cột" in found
    assert any(p.startswith("Phần 6: ít nhất 5 việc") for p in found)
    assert any(p.startswith("Phần 4: nguyên nhân") for p in found)
