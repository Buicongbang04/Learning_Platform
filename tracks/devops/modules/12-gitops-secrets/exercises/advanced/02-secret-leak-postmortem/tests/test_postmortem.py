import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TIME = re.compile(r"^\|\s*(\d{2}):(\d{2})\s*\|")
DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
CONTAIN = ("xoay", "rotate", "thu hồi", "revoke", "đổi mật khẩu")
PURGE = ("filter-repo", "bfg", "xoá lịch sử", "viết lại lịch sử", "force push", "force-push")
KEYWORDS = {
    2: (("staging",), ("production",), ("phút",)),
    4: (("giải mã", "decrypt", ".dec.yaml"), ("khoá riêng", "private key", "age-secret-key"),
        ("pre-commit", "push protection", "hook", "gitignore")),
    5: (CONTAIN, ("updatekeys", "recipient", "khoá age mới"), PURGE, ("argocd",)),
    6: (("secret scanning", "cảnh báo", "alert"), ("phút",)),
    8: (("pre-commit", "gitleaks", "push protection"), ("định kỳ", "tự động", "ttl", "dynamic")),
}
MIN_BULLETS = {4: 3, 7: 4}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def table_rows(text: str) -> list[list[str]]:
    rows = [line for line in text.splitlines() if line.strip().startswith("|")]
    return [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in rows[2:]]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```", "-"))).strip()


def first(text: str, words) -> int:
    hits = [text.find(w) for w in words if w in text]
    return min(hits) if hits else -1


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
    recovery = section(doc, 5).lower()
    contain, purge = first(recovery, CONTAIN), first(recovery, PURGE)
    if contain != -1 and purge != -1 and purge < contain:
        found.append("Phần 5: xoay hay thu hồi secret phải đứng trước việc xoá khỏi lịch sử git (git không thu hồi được bản đã bị chép)")
    actions = table_rows(section(doc, 8))
    if len(actions) < 5:
        found.append(f"Phần 8: cần ít nhất 5 action item trong bảng, có {len(actions)}")
    elif not all(len(row) >= 3 and row[1] and DATE.search(" ".join(row)) for row in actions):
        found.append("Phần 8: mỗi action item cần người phụ trách (cột 2) và hạn dạng YYYY-MM-DD")
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = " ".join(section(doc, number).split()).lower()
        for group in groups:
            if not any(word in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


def test_postmortem():
    found = postmortem_problems(ex.read("POSTMORTEM.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = postmortem_problems((FIXTURES / "POSTMORTEM.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and any(f.startswith("Phần 3: timeline cần") for f in found)


def test_checks_catch_weak_postmortem():
    found = "\n".join(postmortem_problems((FIXTURES / "POSTMORTEM.weak.md").read_text(encoding="utf-8")))
    for needle in ("Phần 3: timeline phải theo thứ tự", "Phần 5: xoay hay thu hồi secret phải đứng trước",
                   "Phần 8: mỗi action item cần người phụ trách", "Phần 4: chưa nói tới khoá riêng", "Phần 7: ít nhất 4"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_postmortem_passes():
    found = postmortem_problems((FIXTURES / "POSTMORTEM.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)
