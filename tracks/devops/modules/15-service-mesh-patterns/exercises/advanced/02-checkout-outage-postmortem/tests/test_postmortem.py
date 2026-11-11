import csv
import re
from datetime import date
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
EVIDENCE = FIXTURES / "evidence" / "metrics.csv"
SAMPLE = FIXTURES / "sample" / "metrics.csv"
OUTAGE_ERROR_PCT = 5
GROUPS = {"availability", "data management", "design & implementation", "management & monitoring"}
PATTERNS = {
    "retry": {"availability"}, "circuit breaker": {"availability"}, "bulkhead": {"availability"},
    "throttling": {"availability"}, "rate limiting": {"availability"}, "queue-based load leveling": {"availability"},
    "deployment stamps": {"availability"}, "health endpoint monitoring": {"availability", "management & monitoring"},
    "cache-aside": {"data management"}, "cqrs": {"data management"}, "event sourcing": {"data management"},
    "materialized view": {"data management"}, "sharding": {"data management"}, "saga": {"data management"},
    "compensating transaction": {"data management"}, "transactional outbox": {"data management"},
    "sidecar": {"design & implementation"}, "ambassador": {"design & implementation"},
    "anti-corruption layer": {"design & implementation"}, "strangler fig": {"design & implementation"},
    "backends for frontends": {"design & implementation"}, "gateway routing": {"design & implementation", "management & monitoring"},
    "gateway offloading": {"design & implementation", "management & monitoring"},
    "external configuration store": {"management & monitoring"},
}
KINDS = {"phòng ngừa", "phát hiện", "giảm thiểu"}
TIME = re.compile(r"\b([01]\d|2[0-3]):([0-5]\d)\b")


def facts(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    outage = [r for r in rows if float(r["payments_error_pct"]) >= OUTAGE_ERROR_PCT]
    peak = max(rows, key=lambda r: float(r["payments_rps"]))
    return {"minutes": len(outage), "start": outage[0]["minute"] if outage else None, "failed": sum(int(r["orders_failed"]) for r in rows),
            "peak_minute": peak["minute"], "peak_in": peak["checkout_rps"], "peak_payments": peak["payments_rps"]}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def subsection(text: str, title: str) -> str:
    match = re.search(rf"^### {title}\s*$(.*?)(?=^### |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*-\s+(.+)$", text, re.M)]


def steps(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*\d+\.\s+(.+)$", text, re.M)]


def table(text: str) -> tuple[list[str], list[dict]]:
    lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return [], []
    split = [[cell.strip().strip("`").strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    header = [cell.lower() for cell in split[0]]
    return header, [dict(zip(header, row)) for row in split[2:]]


def numbers(text: str) -> set[str]:
    joined = re.sub(r"(?<=\d)[ ., ](?=\d{3}\b)", "", text)
    return set(re.findall(r"\d+", joined))


def doc_problems(doc: str, data: dict, incident_day: date) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    summary = section(doc, 1)
    if len(bullets(summary)) < 3:
        found.append("Phần 1: ít nhất 3 gạch đầu dòng")
    if str(data["minutes"]) not in numbers(summary):
        found.append(f"Phần 1: nêu thời lượng sự cố bằng số phút (số phút payments lỗi từ {OUTAGE_ERROR_PCT}% trở lên trong metrics)")
    impact = numbers(section(doc, 2))
    if str(data["failed"]) not in impact:
        found.append("Phần 2: nêu tổng số đơn thất bại, cộng từ cột orders_failed")
    if not {data["peak_in"], data["peak_payments"]} <= impact:
        found.append(f"Phần 2: nêu lưu lượng vào checkout và vào payments ở phút payments nhận nhiều request nhất ({data['peak_minute']})")
    header, events = table(section(doc, 3))
    if header[:2] != ["thời điểm", "sự kiện"]:
        found.append("Phần 3: bảng cần cột 'Thời điểm', 'Sự kiện'")
        events = []
    elif len(events) < 6:
        found.append(f"Phần 3: ít nhất 6 mốc, có {len(events)}")
    times = [TIME.search(e.get("thời điểm", "")) for e in events]
    if events and not all(times):
        found.append("Phần 3: mỗi mốc ghi giờ dạng HH:MM")
    elif events:
        minutes = [int(t.group(1)) * 60 + int(t.group(2)) for t in times]
        if minutes != sorted(minutes):
            found.append("Phần 3: các mốc phải theo thứ tự thời gian")
        if data["start"] and data["start"] not in {f"{t.group(1)}:{t.group(2)}" for t in times}:
            found.append(f"Phần 3: có mốc lúc tỉ lệ lỗi payments bắt đầu vượt {OUTAGE_ERROR_PCT}% ({data['start']})")
    cause = section(doc, 4)
    if len(steps(subsection(cause, "Vì sao"))) < 3:
        found.append("Phần 4: mục 'Vì sao' cần ít nhất 3 bước đánh số")
    if len(bullets(subsection(cause, "Yếu tố góp phần"))) < 2:
        found.append("Phần 4: mục 'Yếu tố góp phần' cần ít nhất 2 gạch đầu dòng")
    header, reviews = table(section(doc, 5))
    if header[:4] != ["pattern", "nhóm", "hiện trạng", "đề xuất"]:
        found.append("Phần 5: bảng cần cột 'Pattern', 'Nhóm', 'Hiện trạng', 'Đề xuất'")
        reviews = []
    elif len(reviews) < 6:
        found.append(f"Phần 5: ít nhất 6 pattern, có {len(reviews)}")
    covered = set()
    for row in reviews:
        name, group = row.get("pattern", "").lower(), row.get("nhóm", "").lower()
        if group not in GROUPS:
            found.append(f"Phần 5: nhóm {row.get('nhóm')!r} không thuộc {sorted(GROUPS)}")
        elif name not in PATTERNS:
            found.append(f"Phần 5: pattern {row.get('pattern')!r} không có trong danh sách của README")
        elif group not in PATTERNS[name]:
            found.append(f"Phần 5: {row.get('pattern')} không thuộc nhóm {row.get('nhóm')}")
        else:
            covered.add(group)
        if not row.get("hiện trạng") or not row.get("đề xuất"):
            found.append(f"Phần 5: {row.get('pattern')!r} cần cả hiện trạng và đề xuất")
    if reviews and covered != GROUPS:
        found.append(f"Phần 5: phủ đủ bốn nhóm, còn thiếu {sorted(GROUPS - covered)}")
    header, actions = table(section(doc, 6))
    if header[:4] != ["việc", "loại", "người phụ trách", "hạn"]:
        found.append("Phần 6: bảng cần cột 'Việc', 'Loại', 'Người phụ trách', 'Hạn'")
        actions = []
    elif len(actions) < 5:
        found.append(f"Phần 6: ít nhất 5 việc, có {len(actions)}")
    kinds = {a.get("loại", "").lower() for a in actions}
    if actions and not KINDS <= kinds:
        found.append(f"Phần 6: cần đủ ba loại {sorted(KINDS)}, còn thiếu {sorted(KINDS - kinds)}")
    for action in actions:
        try:
            due = date.fromisoformat(action.get("hạn", ""))
        except ValueError:
            found.append(f"Phần 6: hạn của {action.get('việc')!r} viết dạng YYYY-MM-DD")
            continue
        if due <= incident_day:
            found.append(f"Phần 6: hạn của {action.get('việc')!r} phải sau ngày sự cố")
        if not action.get("người phụ trách"):
            found.append(f"Phần 6: {action.get('việc')!r} cần người phụ trách")
    if len(bullets(section(doc, 7))) < 2:
        found.append("Phần 7: ít nhất 2 bài học")
    return found


def test_postmortem_document():
    found = doc_problems(ex.read("POSTMORTEM.md"), facts(EVIDENCE), date(2026, 11, 27))
    assert not found, "\n".join(found)


def test_evidence_is_consistent():
    data = facts(EVIDENCE)
    assert data["minutes"] > 0 and data["failed"] > 0 and data["start"], data


def test_checks_catch_template():
    found = doc_problems((FIXTURES / "POSTMORTEM.template.md").read_text(encoding="utf-8"), facts(EVIDENCE), date(2026, 11, 27))
    assert "Còn TODO" in found and any(f.startswith("Phần 5: ít nhất 6 pattern") for f in found), found


def test_checks_catch_weak_document():
    found = "\n".join(doc_problems((FIXTURES / "POSTMORTEM.weak.md").read_text(encoding="utf-8"), facts(SAMPLE), date(2026, 10, 14)))
    for needle in ("Phần 1: nêu thời lượng", "tổng số đơn thất bại", "theo thứ tự thời gian", "phủ đủ bốn nhóm",
                   "không thuộc nhóm", "cần đủ ba loại", "phải sau ngày sự cố"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_document_passes():
    found = doc_problems((FIXTURES / "POSTMORTEM.good.md").read_text(encoding="utf-8"), facts(SAMPLE), date(2026, 10, 14))
    assert not found, "\n".join(found)
