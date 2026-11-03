import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TYPES = {"counter", "gauge", "histogram", "info"}
BANNED_LABELS = {"request_id", "user_id", "trip_id", "session_id", "rider_id", "driver_id", "ip", "email", "url", "path", "timestamp"}
CAUSE_WORDS = re.compile(r"\b(cpu|ram|memory|bộ nhớ|disk|đĩa)\b", re.I)
SERIES_BUDGET = 20000


def section(doc, number):
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text):
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text):
    return re.findall(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)


def prose(text):
    kept, fenced = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        elif not fenced and not line.strip().startswith("|"):
            kept.append(line)
    return "\n".join(kept).strip()


def labels_of(cell):
    cell = cell.strip()
    if cell in ("-", ""):
        return []
    return re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\((\d+)\)", cell)


def minutes(text):
    match = re.fullmatch(r"(\d+)\s*([smh])", text.strip())
    return int(match.group(1)) * {"s": 1 / 60, "m": 1, "h": 60}[match.group(2)] if match else None


def problems(doc):
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for n in range(1, 7):
        if not re.search(rf"^## {n}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {n}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 2), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 6:
        found.append("Phần 2: cần khối mermaid có ít nhất 6 cạnh")
    metrics = [r for r in table_rows(section(doc, 3)) if len(r) >= 4 and all(r[:4])]
    if len(metrics) < 8:
        found.append("Phần 3: bảng ít nhất 8 metric đủ 4 cột")
    total = 0
    for name, kind, labels, series in metrics:
        if kind.lower() not in TYPES:
            found.append(f"Phần 3: '{name}' có loại '{kind}' không hợp lệ")
        pairs = labels_of(labels)
        if labels.strip() not in ("-", "") and not pairs:
            found.append(f"Phần 3: '{name}' ghi label sai dạng tên(số giá trị)")
        for label, _ in pairs:
            if label.lower() in BANNED_LABELS:
                found.append(f"Phần 3: '{name}' dùng label cardinality cao '{label}'")
        product = 1
        for _, count in pairs:
            product *= int(count)
        if not series.isdigit():
            found.append(f"Phần 3: '{name}' cột Series tối đa phải là số nguyên")
            continue
        if int(series) < product:
            found.append(f"Phần 3: '{name}' ghi {series} series nhưng tích số giá trị label là {product}")
        total += int(series)
    if total > SERIES_BUDGET:
        found.append(f"Phần 3: tổng series {total} vượt ngân sách {SERIES_BUDGET}")
    kinds = {r[1].lower() for r in metrics}
    if not {"histogram", "info"} <= kinds:
        found.append("Phần 3: cần ít nhất một histogram và một info metric")
    alerts = [r for r in table_rows(section(doc, 4)) if len(r) >= 5 and all(r[:5])]
    if len(alerts) < 6:
        found.append("Phần 4: bảng ít nhất 6 alert đủ 5 cột (Runbook không được để trống)")
    severities = [r[2].lower() for r in alerts]
    if any(s not in ("critical", "warning") for s in severities):
        found.append("Phần 4: Severity chỉ là critical hoặc warning")
    if severities.count("critical") < 1 or severities.count("warning") < 2:
        found.append("Phần 4: ít nhất 1 critical và 2 warning")
    for alert, symptom, severity, for_text, _ in alerts:
        value = minutes(for_text)
        if value is None or value < 1:
            found.append(f"Phần 4: '{alert}' có for '{for_text}' không hợp lệ hoặc dưới 1m")
        if severity.lower() == "critical" and CAUSE_WORDS.search(alert + " " + symptom):
            found.append(f"Phần 4: '{alert}' là critical theo nguyên nhân (CPU, RAM, đĩa); critical phải theo triệu chứng")
    text = " ".join(" ".join(r) for r in alerts).lower()
    if not re.search(r"prediction|fallback|phân phối|dự đoán", text):
        found.append("Phần 4: cần ít nhất một alert về metric của model (phân phối dự đoán hoặc fallback)")
    if not re.search(r"absent|mất metric|biến mất", text):
        found.append("Phần 4: cần một alert cho trường hợp metric biến mất (absent)")
    ops = section(doc, 5).lower()
    if len(bullets(ops)) < 4:
        found.append("Phần 5: ít nhất 4 gạch đầu dòng")
    for word in ("retention", "sampling"):
        if word not in ops:
            found.append(f"Phần 5: phải nhắc '{word}'")
    if len(bullets(section(doc, 6))) < 3:
        found.append("Phần 6: ít nhất 3 gạch đầu dòng")
    return found


def test_design_has_required_structure():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_weak_design():
    found = problems((FIXTURES / "DESIGN.bad.md").read_text(encoding="utf-8"))
    assert len(found) >= 8
    assert any("request_id" in f for f in found)
    assert any("critical theo nguyên nhân" in f for f in found)
