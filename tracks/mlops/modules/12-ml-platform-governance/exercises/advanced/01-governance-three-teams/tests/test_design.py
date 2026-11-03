import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TIERS = {"cao", "trung bình", "thấp"}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def table_header(text: str) -> list[str]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [c.strip().lower() for c in rows[0]] if rows else []


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

    s1 = section(doc, 1)
    if len(prose(s1)) < 300:
        found.append("Phần 1: cần ít nhất 300 ký tự văn xuôi")
    if table_header(s1) != ["đội", "tầng", "lý do", "hậu quả khi sai"]:
        found.append("Phần 1: bảng cần đủ 4 cột Đội, Tầng, Lý do, Hậu quả khi sai")
    teams = {r[0].lower(): r for r in table_rows(s1) if len(r) >= 4}
    if set(teams) != {"credit-risk", "recsys", "research"}:
        found.append("Phần 1: bảng cần đúng 3 dòng credit-risk, recsys, research")
    else:
        if any(r[1].lower() not in TIERS for r in teams.values()):
            found.append("Phần 1: cột Tầng chỉ nhận cao, trung bình, thấp")
        if teams["credit-risk"][1].lower() != "cao":
            found.append("Phần 1: credit-risk phải ở tầng cao")
        if teams["research"][1].lower() != "thấp":
            found.append("Phần 1: research phải ở tầng thấp")

    s2 = section(doc, 2)
    if table_header(s2) != ["kiểm soát", "cao", "trung bình", "thấp"]:
        found.append("Phần 2: bảng cần cột Kiểm soát, Cao, Trung bình, Thấp")
    rows = [r for r in table_rows(s2) if len(r) >= 4]
    if len(rows) < 6:
        found.append("Phần 2: ít nhất 6 dòng")
    if any(not all(r[:4]) for r in rows):
        found.append("Phần 2: không được có ô trống")
    if sum(1 for r in rows if r[1].strip().lower() != r[3].strip().lower()) < 4:
        found.append("Phần 2: ít nhất 4 dòng có ô Cao khác ô Thấp")
    approval = [r for r in rows if "duyệt" in r[0].lower()]
    if not any(re.search(r"hai người|2 người", r[1], re.I) for r in approval):
        found.append("Phần 2: dòng duyệt phải nói rõ hai người ở tầng Cao")

    s3 = section(doc, 3)
    if len(bullets(s3)) < 4:
        found.append("Phần 3: ít nhất 4 gạch đầu dòng")
    if "tự duyệt" not in s3.lower():
        found.append("Phần 3: phải nêu người train không được tự duyệt")

    s4 = section(doc, 4).lower()
    for word in ("audit log", "hash", "retention"):
        if word not in s4:
            found.append(f"Phần 4: phải nhắc '{word}'")
    years = [int(n) for n in re.findall(r"(\d+)\s*năm", s4)]
    if not re.search(r"\d+\s*(năm|tháng|ngày)", s4):
        found.append("Phần 4: cần con số lưu giữ có đơn vị")
    if not years or max(years) < 5:
        found.append("Phần 4: tầng cao phải lưu giữ ít nhất 5 năm")

    s5 = section(doc, 5)
    diagram = re.search(r"```mermaid\n(.*?)```", s5, re.S)
    if not diagram or len(re.findall(r"-->", diagram.group(1))) < 6:
        found.append("Phần 5: cần khối mermaid có ít nhất 6 cạnh")
    if "rollback" not in s5.lower():
        found.append("Phần 5: sơ đồ phải có rollback")

    s6 = section(doc, 6).lower()
    if len(bullets(s6)) < 4:
        found.append("Phần 6: ít nhất 4 gạch đầu dòng")
    if "ngân sách" not in s6 and "budget" not in s6:
        found.append("Phần 6: phải nhắc ngân sách hoặc budget")
    return found


def test_design_has_required_structure():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_weak_design():
    found = problems((FIXTURES / "DESIGN.bad.md").read_text(encoding="utf-8"))
    assert len(found) >= 8
    assert any("credit-risk phải ở tầng cao" in f for f in found)
    assert any("hai người" in f for f in found)
    assert any("tự duyệt" in f for f in found)
