import math
import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
OPTIONS = ["Tự dựng", "Cloud", "Lai"]


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table(text: str) -> tuple[list[str], list[list[str]]]:
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        return [], []
    return [c.lower() for c in rows[0]], rows[2:]


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


def number(cell: str):
    cleaned = re.sub(r"[^\d.\-]", "", cell.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def weighted_totals(doc: str) -> list[float] | None:
    header, rows = table(section(doc, 2))
    if header != ["tiêu chí", "trọng số", "tự dựng", "cloud", "lai"]:
        return None
    body = [r for r in rows if len(r) >= 5 and not r[0].lower().startswith("tổng")]
    try:
        return [sum(int(r[1]) * int(r[2 + i]) for r in body) / 100 for i in range(3)]
    except ValueError:
        return None


def problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for n in range(1, 7):
        if not re.search(rf"^## {n}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {n}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: cần ít nhất 300 ký tự văn xuôi")

    header, rows = table(section(doc, 2))
    if header != ["tiêu chí", "trọng số", "tự dựng", "cloud", "lai"]:
        found.append("Phần 2: bảng cần cột Tiêu chí, Trọng số, Tự dựng, Cloud, Lai")
    else:
        body = [r for r in rows if len(r) >= 5 and not r[0].lower().startswith("tổng")]
        total = [r for r in rows if len(r) >= 5 and r[0].lower().startswith("tổng")]
        if len(body) < 6:
            found.append("Phần 2: ít nhất 6 tiêu chí")
        names = " ".join(r[0].lower() for r in body)
        if "chi phí" not in names or "vận hành" not in names:
            found.append("Phần 2: cần tiêu chí chi phí và tiêu chí vận hành")
        try:
            weights = [int(r[1]) for r in body]
            scores = [int(r[i]) for r in body for i in (2, 3, 4)]
        except ValueError:
            found.append("Phần 2: trọng số và điểm phải là số nguyên")
        else:
            if sum(weights) != 100:
                found.append(f"Phần 2: trọng số cộng {sum(weights)}, cần 100")
            if any(not 1 <= s <= 5 for s in scores):
                found.append("Phần 2: điểm phải từ 1 đến 5")
            expected = weighted_totals(doc)
            if not total:
                found.append("Phần 2: thiếu dòng Tổng có trọng số")
            else:
                stated = [number(c) for c in total[-1][2:5]]
                if expected is None or any(s is None or abs(s - round(e, 2)) > 0.005 for s, e in zip(stated, expected)):
                    found.append(f"Phần 2: dòng Tổng không khớp tính toán {expected}")

    header3, rows3 = table(section(doc, 3))
    by_name = {r[0].lower(): r for r in rows3 if len(r) >= 4}
    columns = None
    if header3 != ["hạng mục", "tự dựng", "cloud", "lai"] or not {"chi phí một lần", "chi phí mỗi tháng", "tổng 24 tháng"} <= set(by_name):
        found.append("Phần 3: cần bảng Hạng mục/Tự dựng/Cloud/Lai với ba dòng Chi phí một lần, Chi phí mỗi tháng, Tổng 24 tháng")
    else:
        once, month, tot = (
            [number(c) for c in by_name[k][1:4]] for k in ("chi phí một lần", "chi phí mỗi tháng", "tổng 24 tháng")
        )
        if None in once + month + tot:
            found.append("Phần 3: chi phí phải là số")
        else:
            columns = (once, month)
            if any(abs(t - (o + 24 * m)) > 0.5 for o, m, t in zip(once, month, tot)):
                found.append("Phần 3: Tổng 24 tháng phải bằng một lần + 24 × mỗi tháng")
    match = re.search(r"hoà vốn[^\n]*", prose(section(doc, 3)), re.I)
    if not match:
        found.append("Phần 3: thiếu dòng Điểm hoà vốn")
    elif columns:
        (o_self, o_cloud), (m_self, m_cloud) = (columns[0][0], columns[0][1]), (columns[1][0], columns[1][1])
        crossing = m_cloud > m_self and o_self > o_cloud
        stated = re.search(r"tháng\s*(\d+)", match.group(0), re.I)
        if crossing:
            expected = math.ceil((o_self - o_cloud) / (m_cloud - m_self))
            if not stated or abs(int(stated.group(1)) - expected) > 1:
                found.append(f"Phần 3: điểm hoà vốn phải xấp xỉ tháng {expected}")
        elif "không có" not in match.group(0).lower():
            found.append("Phần 3: hai đường chi phí không cắt nhau, phải ghi 'không có' điểm hoà vốn")

    s4 = section(doc, 4)
    pick = re.search(r"\*\*Khuyến nghị:\*\*\s*(Tự dựng|Cloud|Lai)\b", s4)
    if not pick:
        found.append("Phần 4: cần dòng **Khuyến nghị:** với đúng một phương án")
    else:
        totals = weighted_totals(doc)
        if totals and totals[OPTIONS.index(pick.group(1))] < max(totals) and "lệch khỏi điểm số" not in s4.lower():
            found.append("Phần 4: khuyến nghị không có điểm cao nhất, cần cụm 'lệch khỏi điểm số' và giải thích")

    s5 = bullets(section(doc, 5))
    if len(s5) < 3:
        found.append("Phần 5: ít nhất 3 gạch đầu dòng")
    if any(not re.search(r"\d", b) for b in s5):
        found.append("Phần 5: mỗi điều kiện phải có một con số cụ thể")

    s6 = section(doc, 6)
    if len(bullets(s6)) < 3:
        found.append("Phần 6: ít nhất 3 gạch đầu dòng")
    if "lock-in" not in s6.lower():
        found.append("Phần 6: phải nhắc lock-in")
    return found


def test_decision_has_required_structure_and_consistent_numbers():
    found = problems(ex.read("DECISION.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_weak_decision():
    found = problems((FIXTURES / "DECISION.bad.md").read_text(encoding="utf-8"))
    assert len(found) >= 8
    assert any("trọng số cộng" in f for f in found)
    assert any("Tổng 24 tháng" in f for f in found)
    assert any("hoà vốn" in f for f in found)
    assert any("1 đến 5" in f for f in found)


def test_checker_catches_an_arithmetic_slip():
    doc = (FIXTURES / "DECISION.bad.md").read_text(encoding="utf-8")
    fixed = doc.replace("| Tốc độ | 50 | 5 | 2 | 9 |", "| Tốc độ | 70 | 5 | 2 | 3 |")
    assert any("không khớp tính toán" in f for f in problems(fixed))
