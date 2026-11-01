import re
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TEAMS = {"backend", "payments", "platform", "security", "data"}
OWNER = re.compile(r"^@olist-shop/([a-z]+)$")
REQUIRED_OWNERS = {
    "README.md": {"backend"},
    "services/api/app/main.py": {"backend"},
    "services/worker/tasks.py": {"backend"},
    "services/api/app/payments/pix.py": {"payments", "security"},
    "services/api/migrations/0042_add_pix.sql": {"backend", "data"},
    "services/api/Dockerfile": {"backend", "platform"},
    "analytics/dbt/models/orders.sql": {"data"},
    "infra/tofu/main.tf": {"platform"},
    "tools/legacy/network.tf": {"platform"},
    "deploy/helm/values-prod.yaml": {"platform"},
    ".github/workflows/ci.yml": {"platform", "security"},
    ".github/CODEOWNERS": {"platform", "security"},
}
DORA = {
    "deployment frequency": re.compile(r"deployment frequency|tần suất deploy", re.I),
    "lead time": re.compile(r"lead time", re.I),
    "change failure rate": re.compile(r"change failure", re.I),
    "recovery time": re.compile(r"recovery time|MTTR|thời gian khôi phục", re.I),
}


def pattern_regex(pattern: str) -> re.Pattern:
    """Ngữ nghĩa CODEOWNERS của GitHub, đúng các dạng liệt kê trong đề."""
    anchored = pattern.startswith("/") or "/" in pattern.rstrip("/")
    directory = pattern.endswith("/")
    body = pattern.strip("/")
    out = ""
    i = 0
    while i < len(body):
        if body.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif body.startswith("/**", i) and i + 3 == len(body):
            out += "/.*"
            i += 3
        elif body[i] == "*":
            out += "[^/]*"
            i += 1
        elif body[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(body[i])
            i += 1
    prefix = "^" if anchored else "^(?:.*/)?"
    if directory:
        suffix = "/.*$"
    elif body.endswith("*"):
        suffix = "$"
    else:
        suffix = "(?:/.*)?$"
    return re.compile(prefix + out + suffix)


def parse_codeowners(text: str) -> tuple[list[tuple[str, list[str]]], list[str]]:
    rules, errors = [], []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        pattern, owners = parts[0], parts[1:]
        if pattern.startswith("!") or "[" in pattern or "\\" in pattern:
            errors.append(f"CODEOWNERS dòng {number}: GitHub không hỗ trợ '!', '[ ]', '\\' trong pattern")
        if not owners:
            errors.append(f"CODEOWNERS dòng {number}: '{pattern}' không có owner")
        teams = []
        for owner in owners:
            match = OWNER.match(owner)
            if not match or match.group(1) not in TEAMS:
                errors.append(f"CODEOWNERS dòng {number}: owner '{owner}' không thuộc @olist-shop/{{{','.join(sorted(TEAMS))}}}")
            else:
                teams.append(match.group(1))
        rules.append((pattern, teams))
    return rules, errors


def owners_of(rules: list[tuple[str, list[str]]], path: str) -> set[str]:
    owners: set[str] = set()
    for pattern, teams in rules:
        if pattern_regex(pattern).match(path):
            owners = set(teams)
    return owners


def codeowners_problems(text: str) -> list[str]:
    rules, errors = parse_codeowners(text)
    if "TODO" in text:
        errors.insert(0, "CODEOWNERS: còn TODO")
    for path, expected in REQUIRED_OWNERS.items():
        got = owners_of(rules, path)
        if got != expected:
            errors.append(f"CODEOWNERS: {path} cần owner {sorted(expected)}, đang là {sorted(got)}")
    return errors


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def list_items(text: str, numbered: bool = False) -> list[str]:
    marker = r"\d+\." if numbered else r"(?:\d+\.|-)"
    return [m.group(1).strip() for m in re.finditer(rf"^\s*{marker}\s+(.+)$", text, re.M)]


def strategy_problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    if len(section(doc, 1).strip()) < 250:
        found.append("Phần 1: bối cảnh và ràng buộc cần ít nhất 250 ký tự")
    model = section(doc, 2)
    if not re.search(r"^```mermaid\s*\n\s*gitGraph", model, re.M):
        found.append("Phần 2: cần một khối mermaid gitGraph")
    if len(re.sub(r"```.*?```", "", model, flags=re.S).strip()) < 200:
        found.append("Phần 2: giải thích mô hình nhánh cần ít nhất 200 ký tự ngoài sơ đồ")
    envs = [r for r in table_rows(section(doc, 3)) if len(r) >= 5 and all(r[:5])]
    names = " ".join(r[0].lower() for r in envs)
    if len(envs) < 3 or not all(env in names for env in ("dev", "staging", "prod")):
        found.append("Phần 3: bảng cần ít nhất 3 dòng đủ 5 cột, cột đầu có dev, staging, prod")
    if len(list_items(section(doc, 4), numbered=True)) < 4:
        found.append("Phần 4: luồng hotfix cần ít nhất 4 bước đánh số")
    rules = [r for r in table_rows(section(doc, 5)) if len(r) >= 3 and all(r[:3])]
    if len(rules) < 4:
        found.append("Phần 5: bảng ruleset cần ít nhất 4 dòng đủ 3 cột")
    dora = section(doc, 6)
    named = [name for name, pattern in DORA.items() if pattern.search(dora)]
    if len(list_items(dora)) < 3 or len(named) < 3:
        found.append("Phần 6: ít nhất 3 gạch đầu dòng, nhắc ít nhất 3 trong 4 chỉ số DORA")
    if len(list_items(section(doc, 7))) < 3:
        found.append("Phần 7: ít nhất 3 đánh đổi hoặc tín hiệu xem lại")
    return found


def test_strategy_document():
    found = strategy_problems(ex.read("STRATEGY.md"))
    assert not found, "\n".join(found)


def test_codeowners():
    found = codeowners_problems(ex.read("CODEOWNERS"))
    assert not found, "\n".join(found)


def test_checks_catch_templates():
    strategy = strategy_problems((FIXTURES / "STRATEGY.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in strategy
    assert any(p.startswith("Phần 2") for p in strategy)
    assert any(p.startswith("Phần 6") for p in strategy)
    owners = codeowners_problems((FIXTURES / "CODEOWNERS.template").read_text(encoding="utf-8"))
    assert any("còn TODO" in p for p in owners)


def test_default_rule_last_is_caught():
    """Lỗi hay gặp nhất: dòng '*' đặt cuối tệp đè mọi dòng trước nó (dòng khớp sau cùng thắng)."""
    found = codeowners_problems((FIXTURES / "CODEOWNERS.default-last").read_text(encoding="utf-8"))
    assert "CODEOWNERS: infra/tofu/main.tf cần owner ['platform'], đang là ['backend']" in found


@pytest.mark.parametrize(
    ("pattern", "path", "match"),
    [
        ("*", "a/b/c.py", True),
        ("*.tf", "tools/legacy/network.tf", True),
        ("*.tf", "main.tf.bak", False),
        ("/infra/", "infra/tofu/main.tf", True),
        ("/infra/", "tools/infra/x", False),
        ("docs/", "services/api/docs/a.md", True),
        ("/docs/*", "docs/a.md", True),
        ("/docs/*", "docs/sub/a.md", False),
        ("**/logs", "deep/nested/logs/x", True),
        ("Dockerfile", "services/api/Dockerfile", True),
        ("/.github/CODEOWNERS", ".github/CODEOWNERS", True),
        ("/services/api/", "services/api2/x", False),
    ],
)
def test_matcher_semantics(pattern, path, match):
    assert bool(pattern_regex(pattern).match(path)) is match


def test_last_match_wins():
    rules, errors = parse_codeowners("* @olist-shop/backend\n/infra/ @olist-shop/platform\n")
    assert not errors
    assert owners_of(rules, "infra/x.tf") == {"platform"}
    assert owners_of(rules, "api/x.py") == {"backend"}
