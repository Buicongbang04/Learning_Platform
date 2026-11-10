import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TIME = re.compile(r"^\|\s*(\d{2}):(\d{2})\s*\|")
DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
MIN_BULLETS = {4: 3, 6: 3, 7: 3}
KEYWORDS = {
    2: (("phút",), ("đơn", "order"), ("khách", "customer")),
    5: (("phút",), ("rollback", "quay lại", "roll back")),
    6: (("watchdog", "deadman", "heartbeat"),),
}
MECHANISM = (("inhibit",), ("equal",), ("maintenancemode", "bảo trì", "maintenance"))
PREVENTION = (("equal", "silence"), ("alertmanager thật", "alert giả", "alert thử", "end-to-end", "e2e", "amtool alert"))


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def flat(text: str) -> str:
    return " ".join(text.split()).lower()


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def table_rows(text: str) -> list[list[str]]:
    rows = [line for line in text.splitlines() if line.strip().startswith("|")]
    return [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in rows[2:]]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```", "-"))).strip()


def numbers(text: str) -> set[int]:
    return {int(n) for n in re.findall(r"(?<![\d:.,])(\d+)(?![\d:])", text)}


def postmortem_problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 9):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 250:
        found.append("Phần 1: tóm tắt cần ít nhất 250 ký tự văn xuôi")
    times = [(int(m.group(1)), int(m.group(2))) for line in section(doc, 3).splitlines() if (m := TIME.match(line.strip()))]
    if len(times) < 8:
        found.append(f"Phần 3: timeline cần ít nhất 8 dòng bảng bắt đầu bằng giờ HH:MM, có {len(times)}")
    elif times != sorted(times):
        found.append("Phần 3: timeline phải theo thứ tự thời gian")
    actions = table_rows(section(doc, 8))
    if len(actions) < 5:
        found.append(f"Phần 8: cần ít nhất 5 action item trong bảng, có {len(actions)}")
    elif not all(len(row) >= 3 and row[1] and DATE.search(" ".join(row)) for row in actions):
        found.append("Phần 8: mỗi action item cần người phụ trách (cột 2) và hạn dạng YYYY-MM-DD")
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = flat(section(doc, number))
        for group in groups:
            if not any(word in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


def test_postmortem():
    found = postmortem_problems(ex.read("POSTMORTEM.md"))
    assert not found, "\n".join(found)


def test_impact_and_detection_minutes():
    doc = ex.read("POSTMORTEM.md")
    assert 56 in numbers(section(doc, 2)), "Phần 2: thời gian khách bị ảnh hưởng (số phút) chưa khớp dữ kiện"
    assert 36 in numbers(section(doc, 5)), "Phần 5: thời gian từ lúc bắt đầu lỗi tới lúc con người biết (số phút) chưa khớp dữ kiện"


def test_root_cause_names_mechanism():
    text = flat(section(ex.read("POSTMORTEM.md"), 4))
    assert all(any(word in text for word in group) for group in MECHANISM), \
        "Phần 4: chưa chỉ ra cơ chế cụ thể trong cấu hình khiến alert không tới người trực, và phần thiếu trong đó (đối chiếu evidence/)"


def test_action_items_prevent_mechanism():
    text = flat(section(ex.read("POSTMORTEM.md"), 8))
    assert all(any(word in text for word in group) for group in PREVENTION), \
        "Phần 8: action item chưa chặn đúng cơ chế ở phần 4, hoặc chưa có cách kiểm cấu hình alert trên hệ thống chạy thật"


def test_checks_catch_template():
    found = postmortem_problems((FIXTURES / "POSTMORTEM.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and any(f.startswith("Phần 3: timeline cần") for f in found)


def test_checks_catch_weak_postmortem():
    found = "\n".join(postmortem_problems((FIXTURES / "POSTMORTEM.weak.md").read_text(encoding="utf-8")))
    for needle in ("Phần 3: timeline phải theo thứ tự", "Phần 8: mỗi action item cần người phụ trách", "Phần 6: chưa nói tới watchdog",
                   "Phần 7: ít nhất 3", "Phần 1: tóm tắt cần"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_postmortem_passes():
    found = postmortem_problems((FIXTURES / "POSTMORTEM.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)
