import re

from testkit import Exercise

ex = Exercise(__file__)
TRIGGERS = re.compile(r"push|pull_request|schedule|workflow_dispatch|alias|release|tag", re.I)
GATE_WORDS = re.compile(r"cổng|gate|duyệt|approval|bắt buộc|required", re.I)


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


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
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 2), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 8:
        found.append("Phần 2: cần khối mermaid có ít nhất 8 cạnh")
    rows = [r for r in table_rows(section(doc, 3)) if len(r) >= 4 and all(r[:4])]
    if len(rows) < 5:
        found.append("Phần 3: bảng ít nhất 5 workflow đủ 4 cột")
    for name, trigger, gate, _ in (r[:4] for r in rows):
        if not TRIGGERS.search(trigger):
            found.append(f"Phần 3: workflow '{name}' có cột Trigger không nêu sự kiện cụ thể")
        if re.search(r"deploy|cd\b|release|phát hành", name, re.I) and not GATE_WORDS.search(gate):
            found.append(f"Phần 3: '{name}' deploy mà cột 'Chặn' không nêu cổng hay người duyệt")
    triggers = " ".join(r[1] for r in rows).lower()
    for word in ("paths", "schedule", "alias", "workflow_dispatch"):
        if word not in triggers:
            found.append(f"Phần 3: không dòng nào dùng '{word}' trong cột Trigger")
    seam = section(doc, 4).lower()
    if len(bullets(seam)) < 4:
        found.append("Phần 4: ít nhất 4 gạch đầu dòng")
    if "alias" not in seam or not re.search(r"digest|commit|sha", seam):
        found.append("Phần 4: nói rõ alias đổi thì kích hoạt gì, và định danh nào (digest, commit, sha) được kiểm ở cả hai đầu")
    safety = section(doc, 5).lower()
    if len(bullets(safety)) < 4:
        found.append("Phần 5: ít nhất 4 gạch đầu dòng")
    for word in ("oidc", "permissions", "fork"):
        if word not in safety:
            found.append(f"Phần 5: thiếu '{word}'")
    risks = section(doc, 6).lower()
    if len(bullets(risks)) < 4:
        found.append("Phần 6: ít nhất 4 gạch đầu dòng")
    for word in ("cache", "concurrency", "self-hosted"):
        if word not in risks:
            found.append(f"Phần 6: thiếu '{word}'")
    return found


def test_design_document_is_complete():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_validator_rejects_an_unfinished_document():
    assert problems("# x\n\n## 1. Bối cảnh\n\nTODO\n")
