import re
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
LOCKS = ("use_lockfile", "dynamodb")
KEYWORDS = {
    1: (("tài khoản", "account"), ("môi trường", "environment")),
    4: (("workspace",), ("thư mục", "directory")),
    5: (("ref=", "version"), (".terraform.lock.hcl",), ("promote", "promotion", "nâng bản")),
    7: (("encryption", "mã hoá state"), ("ephemeral", "write-only", "value_wo"), ("OIDC",), ("KMS",)),
}
MIN_BULLETS = {5: 4, 7: 4, 8: 4}
SECRET_IN_TFVARS = re.compile(r"\.tfvars.*(password|secret|mật khẩu|token|passphrase)|(password|secret|mật khẩu|token|passphrase).*\.tfvars", re.I)
NEGATION = re.compile(r"\b(?:không|cấm|chặn|tránh|bỏ|thay vì|never|no|not|avoid)\b", re.I)


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


def stores_secret_in_tfvars(text: str) -> bool:
    return any(SECRET_IN_TFVARS.search(line) and not NEGATION.search(line) for line in text.splitlines())


def tree_problems(doc: str) -> list[str]:
    blocks = re.findall(r"```(?:text|plain)?\n(.*?)```", section(doc, 2), re.S)
    text = "\n".join(blocks)
    if not text.strip():
        return ["Phần 2: cần cây thư mục trong một khối ```text"]
    return [f"Phần 2: cây thư mục chưa có {word}" for word in ("modules/", "dev", "staging", "prod") if word not in text]


def state_problems(doc: str) -> list[str]:
    rows = full_rows(section(doc, 3), 5)
    found = [] if len(rows) >= 4 else ["Phần 3: ít nhất 4 stack đủ 5 cột (Stack, Backend key, Khoá, Ai được apply, Blast radius)"]
    keys = [r[1].strip("`") for r in rows]
    if len(set(keys)) != len(keys):
        found.append("Phần 3: mỗi stack phải có backend key riêng")
    if rows and not any("prod" in key for key in keys):
        found.append("Phần 3: thiếu stack của prod")
    if any(not any(lock in r[2].lower() for lock in LOCKS) for r in rows):
        found.append("Phần 3: mỗi stack phải ghi cách khoá state (use_lockfile hay dynamodb)")
    return found


def pipeline_problems(doc: str) -> list[str]:
    blocks = re.findall(r"```mermaid\n(.*?)```", section(doc, 6), re.S)
    if not blocks:
        return ["Phần 6: cần một khối mermaid"]
    text = "\n".join(blocks).lower()
    found = [f"Phần 6: sơ đồ chưa có {word}" for word in ("plan", "apply", "drift") if word not in text]
    if not re.search(r"approv|phê duyệt|duyệt", text):
        found.append("Phần 6: sơ đồ chưa có bước phê duyệt")
    return found


def problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 9):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    if len(prose(section(doc, 4))) < 200:
        found.append("Phần 4: lập luận workspace hay thư mục cần ít nhất 200 ký tự")
    found += tree_problems(doc) + state_problems(doc) + pipeline_problems(doc)
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = section(doc, number).lower()
        for group in groups:
            if not any(word.lower() in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    if stores_secret_in_tfvars(doc):
        found.append("Không được để secret (password, token, passphrase) trong tệp .tfvars")
    return found


def test_design_document():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "DESIGN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert any(p.startswith("Phần 3: ít nhất 4") for p in found)
    assert "Phần 6: cần một khối mermaid" in found


def test_checks_catch_weak_design():
    found = "\n".join(problems((FIXTURES / "DESIGN.weak.md").read_text(encoding="utf-8")))
    for needle in ("mỗi stack phải có backend key riêng", "thiếu stack của prod", "cách khoá state", "sơ đồ chưa có drift",
                   "bước phê duyệt", "chưa nói tới .terraform.lock.hcl", "chưa nói tới OIDC", "secret",
                   "cây thư mục chưa có modules/"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_design_passes():
    found = problems((FIXTURES / "DESIGN.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


@pytest.mark.parametrize("line,bad", [
    ("- Mật khẩu DB để trong prod.tfvars cho tiện.", True),
    ("- `secrets.auto.tfvars` chứa token GitHub.", True),
    ("- Không bao giờ để password trong .tfvars; CI lấy từ Secrets Manager.", False),
    ("- prod.tfvars chỉ chứa kích thước và số replica.", False),
])
def test_secret_in_tfvars_detection(line, bad):
    assert stores_secret_in_tfvars(line) is bad
