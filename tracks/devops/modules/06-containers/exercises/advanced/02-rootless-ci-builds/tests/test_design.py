import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
CANDIDATES = ("buildkit", "buildah", "kaniko", "podman", "dind", "docker-in-docker")
COLUMNS = ["Phương án", "Cần daemon", "Cần privileged", "Cache", "Đánh đổi"]


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table(text: str) -> tuple[list[str], list[list[str]]]:
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.strip().startswith("|")]
    return (rows[0], rows[2:]) if len(rows) >= 2 else ([], [])


def bullets(text: str, numbered: bool = False) -> list[str]:
    marker = r"\d+\." if numbered else r"(?:-|\d+\.)"
    return [m.group(1).strip() for m in re.finditer(rf"^\s*{marker}\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced and not line.strip().startswith("|"):
            kept.append(line)
    return "\n".join(kept).strip()


def choice_problems(doc: str) -> list[str]:
    header, rows = table(section(doc, 3))
    rows = [r for r in rows if len(r) >= 5 and all(r[:5])]
    found = []
    if header[:5] != COLUMNS:
        found.append(f"Phần 3: bảng phải có đúng các cột {COLUMNS}")
    if len(rows) < 4:
        found.append("Phần 3: so sánh ít nhất 4 phương án đủ 5 cột")
    covered = {c for c in CANDIDATES for r in rows if c in r[0].lower()}
    if len(covered - {"docker-in-docker"}) < 3:
        found.append(f"Phần 3: phải so ít nhất 3 trong BuildKit, Buildah, Kaniko, Podman, DinD; đang có {sorted(covered)}")
    match = re.search(r"^Lựa chọn:\s*(.+)$", section(doc, 4), re.M)
    if not match or "TODO" in match.group(1):
        return found + ["Phần 4: cần dòng 'Lựa chọn: <tên phương án trong bảng phần 3>'"]
    chosen = [r for r in rows if r[0].strip("* `").lower() in match.group(1).lower()]
    if not chosen:
        return found + [f"Phần 4: lựa chọn '{match.group(1).strip()}' không trùng tên phương án nào trong bảng phần 3"]
    if not chosen[0][2].lower().startswith("không"):
        found.append(f"Phần 4: phương án được chọn ({chosen[0][0]}) vẫn cần privileged; chính sách cấm privileged")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 5), re.S)
    if diagram and re.search(r"docker\.sock|privileged", diagram.group(1), re.I):
        found.append("Phần 5: kiến trúc mới vẫn dùng docker.sock hay privileged")
    return found


def problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    risks = section(doc, 2)
    if len(bullets(risks)) < 3 or "docker.sock" not in risks:
        found.append("Phần 2: ít nhất 3 rủi ro, có rủi ro của việc mount docker.sock")
    found += choice_problems(doc)
    if len(prose(section(doc, 4))) < 250:
        found.append("Phần 4: lý do quyết định cần ít nhất 250 ký tự")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 5), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 5:
        found.append("Phần 5: cần một khối mermaid có ít nhất 5 cạnh")
    if len(bullets(section(doc, 6), numbered=True)) < 5:
        found.append("Phần 6: kế hoạch ít nhất 5 bước đánh số")
    if len(bullets(section(doc, 7))) < 4:
        found.append("Phần 7: ít nhất 4 gạch đầu dòng")
    return found


def test_design_document():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "DESIGN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert any(p.startswith("Phần 3: so sánh ít nhất 4") for p in found)
    assert any(p.startswith("Phần 4: cần dòng") for p in found)


def test_checks_catch_privileged_choice():
    found = "\n".join(problems((FIXTURES / "DESIGN.dind.md").read_text(encoding="utf-8")))
    assert "vẫn cần privileged" in found, found
    assert "Phần 5: kiến trúc mới vẫn dùng docker.sock hay privileged" in found, found
