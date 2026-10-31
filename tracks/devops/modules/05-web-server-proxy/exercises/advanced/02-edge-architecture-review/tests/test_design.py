import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
INTERNET = re.compile(r"^(?:0\.0\.0\.0/0|::/0|internet|any|\*)$", re.I)
PUBLIC_PORTS = {"80", "443"}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    kept = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and not line.strip().startswith("|"):
            kept.append(line)
    return "\n".join(kept).strip()


def ports(cell: str) -> set[str]:
    return set(re.findall(r"\d+", cell))


def firewall_problems(doc: str) -> list[str]:
    rules = [r for r in table_rows(section(doc, 4)) if len(r) >= 5 and all(r[:5])]
    found = []
    if len(rules) < 6:
        found.append("Phần 4: ít nhất 6 rule đủ 5 cột")
    for source, target, port, *_ in rules:
        if INTERNET.match(source) and not ports(port) <= PUBLIC_PORTS:
            found.append(f"Phần 4: rule từ {source} tới {target} mở cổng {port}; từ Internet chỉ được mở 80 và 443")
    if not any("5432" in ports(r[2]) and not INTERNET.match(r[0]) for r in rules):
        found.append("Phần 4: cần rule cho Postgres (5432) với nguồn cụ thể, không phải Internet")
    return found


def problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 2), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 6:
        found.append("Phần 2: cần một khối mermaid có ít nhất 6 cạnh")
    decisions = [r for r in table_rows(section(doc, 3)) if len(r) >= 4 and all(r[:4])]
    if len(decisions) < 6:
        found.append("Phần 3: ít nhất 6 quyết định đủ 4 cột")
    found += firewall_problems(doc)
    trust = section(doc, 5)
    if len(bullets(trust)) < 3 or "set_real_ip_from" not in trust or "X-Forwarded-For" not in trust:
        found.append("Phần 5: ít nhất 3 gạch đầu dòng, nêu rõ set_real_ip_from và cách xử lý X-Forwarded-For")
    if len(bullets(section(doc, 6))) < 4:
        found.append("Phần 6: ít nhất 4 gạch đầu dòng có giá trị cụ thể")
    if len(bullets(section(doc, 7))) < 3:
        found.append("Phần 7: ít nhất 3 rủi ro hoặc việc còn mở")
    return found


def test_design_document():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "DESIGN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert any(p.startswith("Phần 3") for p in found)
    assert any(p.startswith("Phần 4: ít nhất 6 rule") for p in found)


def test_checks_catch_database_open_to_internet():
    found = firewall_problems((FIXTURES / "DESIGN.open-db.md").read_text(encoding="utf-8"))
    assert any("5432" in p and "Internet" in p for p in found), found
    assert any("cổng 22" in p for p in found), found
    assert any("Postgres (5432) với nguồn cụ thể" in p for p in found), found
