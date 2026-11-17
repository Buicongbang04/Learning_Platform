import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
DEADLINES = {"CRITICAL": 7, "HIGH": 30}
KEYWORDS = {
    3: (("USER", "non-root"), ("HEALTHCHECK",), ("multi-stage",), ("latest",)),
    5: (("expired_at", "hết hạn"), ("duyệt", "phê duyệt"), ("statement", "lý do")),
    6: (("digest",), ("SBOM",), ("ký", "cosign", "sign")),
    7: (("read_only", "read-only"), ("no-new-privileges",), ("cap_drop", "capabilit")),
}
MIN_BULLETS = {3: 8, 5: 4, 6: 4, 7: 4, 8: 4}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```"))).strip()


def base_image_problems(doc: str) -> list[str]:
    rows = [r for r in table_rows(section(doc, 2)) if len(r) >= 4 and all(r[:4])]
    found = [] if len(rows) >= 3 else ["Phần 2: ít nhất 3 image nền đủ 4 cột"]
    for image, digest, *_ in rows:
        name = image.strip("`")
        tag = name.rsplit(":", 1)[1] if ":" in name.rsplit("/", 1)[-1] else ""
        if not tag or tag == "latest":
            found.append(f"Phần 2: {name} phải ghim tag cụ thể, không để trống hay latest")
        if not DIGEST.search(digest):
            found.append(f"Phần 2: {name} thiếu digest dạng sha256:<64 ký tự hex>")
    return found


def deadline_problems(doc: str) -> list[str]:
    rows = [r for r in table_rows(section(doc, 4)) if len(r) >= 4 and all(r[:4])]
    found = [] if len(rows) >= 4 else ["Phần 4: ít nhất 4 dòng đủ 4 cột (Mức độ, Có bản vá, Thời hạn, Gate)"]
    for level, limit in DEADLINES.items():
        fixed = [r for r in rows if level in r[0].upper() and r[1].lower().startswith("có")]
        if not fixed:
            found.append(f"Phần 4: thiếu dòng {level} có bản vá")
            continue
        days = [int(n) for n in re.findall(r"\d+", fixed[0][2])]
        if not days or max(days) > limit:
            found.append(f"Phần 4: {level} có bản vá phải vá trong tối đa {limit} ngày, đang là '{fixed[0][2]}'")
        if "chặn" not in fixed[0][3].lower():
            found.append(f"Phần 4: {level} có bản vá phải chặn ở gate, đang là '{fixed[0][3]}'")
    return found


def problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 9):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: phạm vi và nguyên tắc cần ít nhất 300 ký tự")
    found += base_image_problems(doc)
    found += deadline_problems(doc)
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = section(doc, number)
        for group in groups:
            if not any(word.lower() in text.lower() for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


def test_policy_document():
    found = problems(ex.read("POLICY.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "POLICY.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert any(p.startswith("Phần 2: ít nhất 3") for p in found)
    assert any(p.startswith("Phần 4: ít nhất 4") for p in found)


def test_checks_catch_weak_policy():
    found = "\n".join(problems((FIXTURES / "POLICY.weak.md").read_text(encoding="utf-8")))
    assert "python:latest phải ghim tag" in found, found
    assert "node:22-alpine thiếu digest" in found, found
    assert "CRITICAL có bản vá phải vá trong tối đa 7 ngày" in found, found
    assert "HIGH có bản vá phải chặn ở gate" in found, found
    assert "Phần 7: chưa nói tới no-new-privileges" in found, found
