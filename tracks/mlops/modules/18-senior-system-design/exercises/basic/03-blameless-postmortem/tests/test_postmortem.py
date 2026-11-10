import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
NAMES = ("Khải", "Quyên", "Thịnh")
BLAME = ("lỗi của", "cẩu thả", "bất cẩn", "đáng lẽ", "cẩn thận hơn", "chú ý hơn", "theo dõi sát hơn")
KINDS = {"ngăn chặn", "phát hiện", "giảm thiệt hại"}
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
    return "\n".join(line for line in text.splitlines() if line.strip() and not line.strip().startswith("|")).strip()


def problems(doc):
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for n in range(1, 7):
        if not re.search(rf"^## {n}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {n}.'")
    for name in NAMES:
        if re.search(rf"(?<!\w){name}(?!\w)", doc):
            found.append(f"Có tên người '{name}': dùng vai trò")
    lowered = doc.lower()
    for phrase in BLAME:
        if phrase in lowered:
            found.append(f"Có cụm đổ lỗi hoặc hành động không kiểm được: '{phrase}'")
    if len(prose(section(doc, 1))) < 150:
        found.append("Phần 1: tóm tắt cần ít nhất 150 ký tự")
    impact = section(doc, 2)
    if len(re.findall(r"\d", impact)) < 3 or len(re.findall(r"\d+(?:[.,]\d+)?", impact)) < 3:
        found.append("Phần 2: tác động cần ít nhất 3 con số")
    percents = [float(p.replace(",", ".")) for p in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", impact)]
    if not any(43 <= p <= 45 for p in percents):
        found.append("Phần 2: phải nêu phần trăm error budget freshness 30 ngày đã tiêu")
    header, rows = table(section(doc, 3))
    if header[:2] != ["thời điểm", "sự kiện"]:
        found.append("Phần 3: bảng cần cột Thời điểm, Sự kiện")
    times = [r[0] for r in rows if r and r[0]]
    if len(rows) < 6:
        found.append("Phần 3: ít nhất 6 mốc")
    if any(not TIME.match(t) for t in times):
        found.append("Phần 3: thời điểm viết dạng HH:MM")
    elif times != sorted(times):
        found.append("Phần 3: mốc phải theo thứ tự thời gian")
    elif "14:05" not in times or "17:15" not in times:
        found.append("Phần 3: phải có mốc bắt đầu và mốc hết tác động")
    if any(len(r) < 2 or not r[1] for r in rows):
        found.append("Phần 3: mỗi mốc cần mô tả sự kiện")
    if len(bullets(section(doc, 4))) < 3:
        found.append("Phần 4: ít nhất 3 gạch đầu dòng nguyên nhân và yếu tố góp phần")
    if len(bullets(section(doc, 5))) < 2:
        found.append("Phần 5: ít nhất 2 gạch đầu dòng")
    header, rows = table(section(doc, 6))
    if header[:5] != ["hành động", "loại", "chủ sở hữu", "hạn", "cách kiểm"]:
        found.append("Phần 6: bảng cần cột Hành động, Loại, Chủ sở hữu, Hạn, Cách kiểm")
    rows = [r for r in rows if len(r) >= 5]
    if len(rows) < 4:
        found.append("Phần 6: ít nhất 4 hành động")
    if any(not all(r[:5]) for r in rows):
        found.append("Phần 6: không được có ô trống")
    kinds = {r[1].lower() for r in rows}
    if kinds - KINDS:
        found.append("Phần 6: cột Loại chỉ nhận ngăn chặn, phát hiện, giảm thiệt hại")
    if not KINDS <= kinds:
        found.append("Phần 6: cần đủ ba loại hành động")
    if any(not DATE.match(r[3]) for r in rows):
        found.append("Phần 6: hạn viết dạng YYYY-MM-DD")
    return found


def test_postmortem_follows_the_template():
    found = problems(ex.read("postmortem.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_blaming_postmortem():
    found = problems((FIXTURES / "postmortem.bad.md").read_text(encoding="utf-8"))
    assert any("tên người" in f for f in found)
    assert any("đổ lỗi" in f for f in found)
    assert any("thứ tự" in f for f in found)
    assert any("ba loại" in f for f in found)
    assert any("phần trăm" in f for f in found)
    assert len(found) >= 6
