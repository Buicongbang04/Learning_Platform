import re
from pathlib import Path

import yaml

from testkit import Exercise

ex = Exercise(__file__)
FIXTURE = Path(__file__).parent / "fixtures" / "vulnerable.yml"

PLANTED = {
    "pull_request_target": (r"^\s*pull_request_target:", r"pull_request_target|fork|đặc quyền|privilege"),
    "checkout_head": (r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head", r"head|fork|không tin cậy|untrusted|checkout"),
    "write_all": (r"permissions:\s*write-all", r"least|tối thiểu|write-all|contents:\s*read|quyền"),
    "injection": (r"echo \"Retrain cho PR \$\{\{", r"injection|inject|env:|không tin cậy|untrusted"),
    "curl_bash": (r"curl .*\|\s*bash", r"checksum|sha256|chữ ký|signature|kiểm tra|verify|ghim|pin"),
    "unpinned_action": (r"uses:\s*acme-org/model-publisher@main", r"sha|ghim|pin|mutable|thay đổi được|tag|nhánh"),
    "secret_echo": (r"echo \"login với token \$\{\{ secrets", r"log|in ra|che|mask|env:|echo"),
    "long_lived_key": (r"AWS_SECRET_ACCESS_KEY:", r"oidc|ngắn hạn|short-lived|dài hạn|long-lived|role"),
}
SEVERITIES = {"high", "medium", "low"}
MUST_BE_HIGH = {"checkout_head", "injection"}


def planted_lines() -> dict[str, int]:
    lines = FIXTURE.read_text().splitlines()
    found = {}
    for name, (pattern, _) in PLANTED.items():
        index = next(i for i, line in enumerate(lines, 1) if re.search(pattern, line))
        found[name] = index
    return found


def evaluate(doc) -> tuple[list[str], set[str]]:
    problems: list[str] = []
    findings = doc.get("findings") if isinstance(doc, dict) else None
    if not isinstance(findings, list) or not findings:
        return ["findings phải là danh sách không rỗng"], set()
    lines = planted_lines()
    caught: dict[str, dict] = {}
    stray = 0
    for item in findings:
        if not isinstance(item, dict) or not isinstance(item.get("line"), int):
            problems.append(f"Mục thiếu 'line' số nguyên: {item!r}")
            continue
        if item.get("severity") not in SEVERITIES:
            problems.append(f"Dòng {item['line']}: severity phải là một trong {sorted(SEVERITIES)}")
        risk, fix = str(item.get("risk", "")), str(item.get("fix", ""))
        if len(risk) < 40 or len(fix) < 30:
            problems.append(f"Dòng {item['line']}: 'risk' cần từ 40 ký tự và 'fix' từ 30 ký tự")
        text = (risk + " " + fix).lower()
        hit = [n for n, line in lines.items() if abs(line - item["line"]) <= 1 and re.search(PLANTED[n][1], text, re.I)]
        if not hit:
            stray += 1
            continue
        caught.setdefault(hit[0], item)
    if len(caught) < 7:
        missing = sorted(set(lines) - set(caught))
        problems.append(f"Mới tìm đúng {len(caught)}/8 lỗi (cần ít nhất 7); chưa thấy: {missing}")
    if stray > 2:
        problems.append(f"{stray} mục không khớp lỗi nào (tối đa 2): đừng báo tràn lan")
    for name in MUST_BE_HIGH & set(caught):
        if caught[name].get("severity") != "high":
            problems.append(f"Lỗi '{name}' phải có severity high")
    return problems, set(caught)


def test_review_covers_the_planted_flaws():
    doc = yaml.safe_load(ex.read("REVIEW.yaml"))
    problems, _ = evaluate(doc)
    assert not problems, "\n".join(problems)


def test_the_checker_rejects_a_scattershot_review():
    shotgun = {"findings": [{"line": n, "severity": "low", "risk": "x" * 50, "fix": "y" * 40} for n in range(1, 40, 3)]}
    problems, caught = evaluate(shotgun)
    assert problems and len(caught) < 7


def test_the_checker_rejects_an_empty_review():
    assert evaluate({"findings": []})[0]
