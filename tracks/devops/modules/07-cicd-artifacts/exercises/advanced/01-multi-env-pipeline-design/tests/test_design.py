import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
STRATEGIES = ("rolling", "blue/green", "blue-green", "canary", "recreate", "feature flag", "shadow")
NO_APPROVAL = {"", "-", "không", "không cần", "tự động", "none", "no"}
KEYWORDS = {
    1: (("lead time", "thời gian từ commit"), ("change failure", "tỉ lệ thay đổi lỗi", "tỷ lệ thay đổi lỗi"),
        ("MTTR", "thời gian khôi phục")),
    5: (("digest",), ("expand",), ("contract",), ("feature flag", "flag")),
    6: (("OIDC",), ("environment",), ("permissions", "quyền tối thiểu")),
}
MIN_BULLETS = {5: 5, 6: 4, 8: 4}


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


def environment_problems(doc: str) -> list[str]:
    rows = full_rows(section(doc, 2), 5)
    found = [] if len(rows) >= 3 else ["Phần 2: ít nhất 3 môi trường đủ 5 cột (Môi trường, Trigger, Phê duyệt, Artifact, Dữ liệu)"]
    by_name = {r[0].strip("`*").lower(): r for r in rows}
    for name in ("staging", "production"):
        row = next((r for key, r in by_name.items() if name in key), None)
        if row is None:
            found.append(f"Phần 2: thiếu dòng {name}")
            continue
        if "digest" not in row[3].lower():
            found.append(f"Phần 2: {name} phải deploy artifact theo digest, đang là '{row[3]}'")
        if "latest" in row[3].lower():
            found.append(f"Phần 2: {name} không được dùng latest")
        if name == "production" and row[2].strip().lower() in NO_APPROVAL:
            found.append(f"Phần 2: production cần phê duyệt hoặc gate rõ ràng, đang là '{row[2]}'")
    return found


def diagram_problems(doc: str) -> list[str]:
    blocks = re.findall(r"```mermaid\n(.*?)```", section(doc, 3), re.S)
    if not blocks:
        return ["Phần 3: cần một khối mermaid"]
    text = "\n".join(blocks).lower()
    return [f"Phần 3: sơ đồ chưa có {word}" for word in ("staging", "production", "rollback") if word not in text]


def strategy_problems(doc: str) -> list[str]:
    rows = full_rows(section(doc, 4), 4)
    found = [] if len(rows) >= 3 else ["Phần 4: ít nhất 3 service đủ 4 cột (Service, Chiến lược, Lý do, Tín hiệu rollback)"]
    used = set()
    for row in rows:
        names = {s for s in STRATEGIES if s in row[1].lower()}
        if not names:
            found.append(f"Phần 4: {row[0]} cần chiến lược trong {', '.join(STRATEGIES)}")
        used |= {"blue/green" if s == "blue-green" else s for s in names}
    if rows and len(used) < 2:
        found.append("Phần 4: các service khác nhau nên có ít nhất 2 chiến lược khác nhau, kèm lý do")
    return found


def gate_problems(doc: str) -> list[str]:
    rows = full_rows(section(doc, 7), 3)
    found = [] if len(rows) >= 4 else ["Phần 7: ít nhất 4 gate đủ 3 cột (Gate, Ngưỡng, Hành động)"]
    if rows and sum(1 for r in rows if re.search(r"\d", r[1])) < 3:
        found.append("Phần 7: ít nhất 3 gate có ngưỡng bằng số")
    text = " ".join(" ".join(r) for r in rows).lower()
    if not re.search(r"lỗi|error|5xx", text):
        found.append("Phần 7: cần một gate theo tỉ lệ lỗi")
    if not re.search(r"p9[059]|latency|độ trễ", text):
        found.append("Phần 7: cần một gate theo độ trễ (p95/p99)")
    return found


def problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 9):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh và mục tiêu cần ít nhất 300 ký tự")
    found += environment_problems(doc) + diagram_problems(doc) + strategy_problems(doc) + gate_problems(doc)
    if re.search(r"write-all|permissions:\s*write", section(doc, 6), re.I):
        found.append("Phần 6: không cấp permissions write-all; mỗi job chỉ nhận quyền nó cần")
    if not re.search(r"\d+\s*phút", section(doc, 5)):
        found.append("Phần 5: cần mục tiêu thời gian rollback tính bằng phút")
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = section(doc, number).lower()
        for group in groups:
            if not any(word.lower() in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


def test_design_document():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "DESIGN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert any(p.startswith("Phần 2: ít nhất 3") for p in found)
    assert "Phần 3: cần một khối mermaid" in found
    assert any(p.startswith("Phần 7: ít nhất 4") for p in found)


def test_checks_catch_weak_design():
    found = "\n".join(problems((FIXTURES / "DESIGN.weak.md").read_text(encoding="utf-8")))
    for needle in ("production phải deploy artifact theo digest", "production không được dùng latest",
                   "production cần phê duyệt", "sơ đồ chưa có rollback", "ít nhất 2 chiến lược khác nhau",
                   "ít nhất 3 gate có ngưỡng bằng số", "theo độ trễ", "mục tiêu thời gian rollback",
                   "chưa nói tới expand", "chưa nói tới OIDC", "không cấp permissions write-all"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
