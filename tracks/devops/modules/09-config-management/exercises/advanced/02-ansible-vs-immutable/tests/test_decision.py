import re
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
CHOICES = {"ansible", "image", "kết hợp"}
WORKLOADS = ("worker", "postgres", "nginx", "bastion")
KEYWORDS = {
    2: (("drift",), ("rollback",), ("boot", "khởi động", "thời gian")),
    4: (("packer", "image builder", "docker build"),),
    5: (("--check",), ("cis",), ("patch", "vá")),
    6: (("vault", "secrets manager", "parameter store"), ("cloud-init", "user-data", "user data")),
}
MIN_BULLETS = {5: 4, 6: 3, 7: 4}
BAKED_SECRET = re.compile(r"(secret|mật khẩu|password|token|bí mật|private key|khoá riêng).*(image|ami)|(image|ami).*(secret|mật khẩu|password|token|bí mật|private key|khoá riêng)", re.I)
NEGATION = re.compile(r"\b(?:không|cấm|chặn|tránh|bỏ|thay vì|never|no|not|avoid|chưa bao giờ)\b", re.I)


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[cell.strip() for cell in row] for row in rows[2:]]


def full_rows(text: str, width: int) -> list[list[str]]:
    return [r for r in table_rows(text) if len(r) >= width and all(r[:width]) and "TODO" not in "".join(r[:width])]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```"))).strip()


def bakes_secret(text: str) -> bool:
    return any(BAKED_SECRET.search(line) and not NEGATION.search(line) for line in text.splitlines())


def decision_problems(doc: str) -> list[str]:
    rows = full_rows(section(doc, 3), 4)
    found = []
    for workload in WORKLOADS:
        if not any(workload in row[0].lower() for row in rows):
            found.append(f"Phần 3: thiếu dòng cho workload {workload}")
    for row in rows:
        if row[1].strip("* ").lower() not in CHOICES:
            found.append(f"Phần 3: cột Chọn của '{row[0]}' phải là Ansible, Image hoặc Kết hợp, đang là '{row[1]}'")
    return found


def flow_problems(doc: str) -> list[str]:
    blocks = re.findall(r"```mermaid\n(.*?)```", section(doc, 4), re.S)
    if not blocks:
        return ["Phần 4: cần một khối mermaid"]
    text = "\n".join(blocks).lower()
    return [f"Phần 4: sơ đồ chưa có {word}" for word in ("build", "image", "ansible", "rollback") if word not in text]


def problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    if len(full_rows(section(doc, 2), 3)) < 6:
        found.append("Phần 2: ít nhất 6 tiêu chí đủ 3 cột")
    found += decision_problems(doc) + flow_problems(doc)
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = section(doc, number).lower()
        for group in groups:
            if not any(word in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    if bakes_secret(doc):
        found.append("Không được nướng secret (mật khẩu, token, khoá riêng) vào image")
    return found


def test_decision_document():
    found = problems(ex.read("DECISION.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "DECISION.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and "Phần 4: cần một khối mermaid" in found
    assert any(p.startswith("Phần 3: thiếu dòng cho workload") for p in found)


def test_checks_catch_weak_decision():
    found = "\n".join(problems((FIXTURES / "DECISION.weak.md").read_text(encoding="utf-8")))
    for needle in ("thiếu dòng cho workload bastion", "cột Chọn của 'Nginx edge'", "sơ đồ chưa có rollback", "chưa nói tới --check",
                   "chưa nói tới cloud-init", "nướng secret", "ít nhất 6 tiêu chí"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_decision_passes():
    found = problems((FIXTURES / "DECISION.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


@pytest.mark.parametrize("line,bad", [
    ("- Mật khẩu database nằm sẵn trong AMI cho máy mới boot nhanh.", True),
    ("- Image chứa token đăng nhập registry.", True),
    ("- Không bao giờ để secret trong image; máy đọc từ Secrets Manager lúc boot.", False),
    ("- Image chỉ chứa code và dependency, cấu hình lấy lúc chạy.", False),
])
def test_baked_secret_detection(line, bad):
    assert bakes_secret(line) is bad
