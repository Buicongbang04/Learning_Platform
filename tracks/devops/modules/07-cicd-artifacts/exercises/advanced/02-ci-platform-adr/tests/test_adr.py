import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
CI_OPTIONS = ("github actions", "gitlab ci", "jenkins", "circleci", "teamcity", "buildkite", "azure pipelines", "tekton")
REPO_OPTIONS = ("artifactory", "nexus", "cloudsmith", "ghcr", "github packages", "harbor", "ecr", "artifact registry")
KEYWORDS = {
    6: (("lock-in", "phụ thuộc nhà cung cấp"), ("chi phí", "USD", "giá")),
    7: (("song song",), ("quay lại", "rollback")),
}
MIN_BULLETS = {6: 4, 7: 4, 8: 2}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def full_rows(text: str, width: int) -> list[list[str]]:
    return [r for r in table_rows(text) if len(r) >= width and all(r[:width]) and "TODO" not in "".join(r[:width])]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```"))).strip()


def number(cell: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", cell)
    return float(match.group(0).replace(",", ".")) if match else None


def criteria_problems(doc: str) -> list[str]:
    rows = full_rows(section(doc, 2), 3)
    if len(rows) < 5:
        return ["Phần 2: ít nhất 5 tiêu chí đủ 3 cột (Tiêu chí, Trọng số, Cách đo)"]
    weights = [number(r[1]) for r in rows]
    if None in weights or abs(sum(weights) - 100) > 0.01:
        return [f"Phần 2: trọng số phải là số và cộng lại đúng 100, đang là {sum(w or 0 for w in weights):g}"]
    return []


def options_problems(doc: str, part: int, known: tuple[str, ...], minimum: int) -> tuple[list[str], str | None]:
    rows = full_rows(section(doc, part), 5)
    found = []
    named = [r for r in rows if any(k in r[0].lower() for k in known)]
    if len(named) < minimum:
        found.append(f"Phần {part}: ít nhất {minimum} phương án đủ 5 cột, tên trong {', '.join(known)}")
    scored = [(number(r[4]), r[0]) for r in named]
    if any(score is None for score, _ in scored):
        found.append(f"Phần {part}: cột Điểm của mọi phương án phải là số")
        return found, None
    if not scored:
        return found, None
    best = max(scored)
    if [s for s, _ in scored].count(best[0]) > 1:
        found.append(f"Phần {part}: có hai phương án cùng điểm cao nhất, phải phân định")
    return found, best[1]


def problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for part in range(1, 9):
        if not re.search(rf"^## {part}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {part}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    found += criteria_problems(doc)
    decision = prose(section(doc, 5)).lower()
    for part, known, minimum in ((3, CI_OPTIONS, 4), (4, REPO_OPTIONS, 3)):
        issues, best = options_problems(doc, part, known, minimum)
        found += issues
        if best and best.strip("`*").lower() not in decision:
            found.append(f"Phần 5: quyết định phải chọn phương án điểm cao nhất của phần {part} ({best}) hoặc sửa điểm cho khớp")
    for part, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, part))) < minimum:
            found.append(f"Phần {part}: ít nhất {minimum} gạch đầu dòng")
    if not re.search(r"\d+\s*(tuần|tháng)", section(doc, 7)):
        found.append("Phần 7: kế hoạch cần mốc thời gian (tuần, tháng)")
    for part, groups in KEYWORDS.items():
        text = section(doc, part).lower()
        for group in groups:
            if not any(word.lower() in text for word in group):
                found.append(f"Phần {part}: chưa nói tới {' / '.join(group)}")
    return found


def test_adr_document():
    found = problems(ex.read("ADR.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "ADR.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert any(p.startswith("Phần 2: ít nhất 5") for p in found)
    assert any(p.startswith("Phần 3: ít nhất 4") for p in found)


def test_checks_catch_weak_adr():
    found = "\n".join(problems((FIXTURES / "ADR.weak.md").read_text(encoding="utf-8")))
    for needle in ("cộng lại đúng 100", "Phần 3: ít nhất 4 phương án", "phương án điểm cao nhất của phần 4 (Nexus Repository Pro)",
                   "Phần 7: kế hoạch cần mốc thời gian", "chưa nói tới song song", "chưa nói tới lock-in"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
