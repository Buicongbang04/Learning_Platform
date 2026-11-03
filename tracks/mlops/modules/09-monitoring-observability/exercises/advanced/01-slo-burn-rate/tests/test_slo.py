import re
from pathlib import Path

import pytest
import yaml

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
HOURS = {"m": 1 / 60, "h": 1, "d": 24}
CAUSE_WORDS = re.compile(r"\b(cpu|ram|memory|disk|goroutine|load average)\b|node_", re.I)
BASE = 'job="eta-service",method="POST",route="/predict"'


def section(doc, number):
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text):
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text):
    return re.findall(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)


def prose(text):
    kept, fenced = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        elif not fenced and not line.strip().startswith("|"):
            kept.append(line)
    return "\n".join(kept).strip()


def hours(text):
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([mhd])", text.strip())
    return float(match.group(1)) * HOURS[match.group(2)] if match else None


def number(text):
    match = re.search(r"\d+(?:[.,]\d+)?", text.replace(" ", ""))
    return float(match.group(0).replace(",", ".")) if match else None


def problems(doc):
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    for n in range(1, 6):
        if not re.search(rf"^## {n}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {n}.'")
    if len(prose(section(doc, 1))) < 200:
        found.append("Phần 1: lời dẫn cần ít nhất 200 ký tự")
    slis = [r for r in table_rows(section(doc, 1)) if len(r) >= 4 and all(r[:4])]
    if len(slis) < 3:
        found.append("Phần 1: bảng ít nhất 3 SLI đủ 4 cột")
    if any(CAUSE_WORDS.search(r[1]) for r in slis):
        found.append("Phần 1: SLI không được đo bằng CPU, RAM, đĩa (nguyên nhân), phải đo thứ người dùng thấy")
    if not any(r[2].startswith("99.5") and r[3].lower() == "30d" for r in slis):
        found.append("Phần 1: phải có SLI khả dụng với SLO 99.5% và cửa sổ 30d")
    budgets = {r[0].lower(): number(r[2]) for r in table_rows(section(doc, 2)) if len(r) >= 3}
    if budgets.get("30d") is None or abs(budgets["30d"] - 216) > 1:
        found.append("Phần 2: budget 30d của SLO 99.5% phải là 216 phút")
    burn = [r for r in table_rows(section(doc, 3)) if len(r) >= 6 and all(r[:6])]
    if len(burn) < 3:
        found.append("Phần 3: bảng ít nhất 3 mức burn rate đủ 6 cột")
    for level, rate, long_w, short_w, percent, action in burn:
        long_h, short_h, rate_n, pct = hours(long_w), hours(short_w), number(rate), number(percent)
        if None in (long_h, short_h, rate_n, pct):
            found.append(f"Phần 3: dòng '{level}' có số hoặc cửa sổ không đọc được")
            continue
        if abs(short_h * 12 - long_h) > 1e-6:
            found.append(f"Phần 3: '{level}' cửa sổ ngắn phải bằng 1/12 cửa sổ dài")
        if abs(rate_n * long_h / 720 * 100 - pct) > 0.3:
            found.append(f"Phần 3: '{level}' % budget tiêu phải bằng burn rate x cửa sổ dài / 720h")
    if burn and not any(re.search(r"page", r[5], re.I) for r in burn):
        found.append("Phần 3: ít nhất một mức có hành động page")
    if burn and not any(re.search(r"ticket", r[5], re.I) for r in burn):
        found.append("Phần 3: ít nhất một mức có hành động ticket")
    diagram = re.search(r"```mermaid\n(.*?)```", section(doc, 4), re.S)
    if not diagram or len(re.findall(r"-->|->>|---", diagram.group(1))) < 4:
        found.append("Phần 4: cần khối mermaid có ít nhất 4 cạnh")
    policy = section(doc, 4)
    if len(bullets(policy)) < 3 or not re.search(r"freeze|đóng băng", policy, re.I):
        found.append("Phần 4: ít nhất 3 gạch đầu dòng và có nhắc freeze hoặc đóng băng")
    if len(bullets(section(doc, 5))) < 3:
        found.append("Phần 5: ít nhất 3 gạch đầu dòng")
    return found


def test_slo_document_has_required_structure():
    found = problems(ex.read("SLO.md"))
    assert not found, "\n".join(found)


def test_checker_catches_a_weak_document():
    found = problems((FIXTURES / "SLO.bad.md").read_text(encoding="utf-8"))
    assert len(found) >= 6
    assert any("CPU" in f for f in found)
    assert any("216" in f for f in found)


@pytest.fixture(scope="module")
def rules_text():
    return ex.read("slo.rules.yml")


def rules_of(text):
    data = yaml.safe_load(text)
    return [rule for group in data["groups"] for rule in group.get("rules", [])]


def test_rules_file_is_valid_and_complete(tmp_path, rules_text):
    (tmp_path / "slo.rules.yml").write_text(rules_text, encoding="utf-8")
    result = mlopskit.promtool("check", "rules", "slo.rules.yml", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    rules = rules_of(rules_text)
    recorded = {r["record"] for r in rules if "record" in r}
    assert {f"eta:http_error_ratio:rate{w}" for w in ("5m", "30m", "1h", "6h")} <= recorded
    alerts = {r["alert"]: r for r in rules if "alert" in r}
    fast, slow = alerts["ETAErrorBudgetFastBurn"], alerts["ETAErrorBudgetSlowBurn"]
    assert fast["labels"]["severity"] == "critical" and slow["labels"]["severity"] == "warning"
    assert re.search(r"\band\b", fast["expr"]) and "rate1h" in fast["expr"] and "rate5m" in fast["expr"]
    assert re.search(r"\band\b", slow["expr"]) and "rate6h" in slow["expr"] and "rate30m" in slow["expr"]
    for alert in (fast, slow):
        assert str(alert["annotations"]["runbook_url"]).startswith("https://")


def run(tmp_path, rules_text, ok, bad, expectations):
    names = {r.get("alert") for r in rules_of(rules_text)}
    assert {"ETAErrorBudgetFastBurn", "ETAErrorBudgetSlowBurn"} <= names, "thiếu alert burn-rate"
    (tmp_path / "slo.rules.yml").write_text(rules_text, encoding="utf-8")
    checks = [{"expr": f'count(ALERTS{{alertname="{name}",alertstate="firing"}})', "eval_time": at,
               "exp_samples": [{"labels": "{}", "value": 1}] if firing else []} for name, at, firing in expectations]
    spec = {"rule_files": ["slo.rules.yml"], "evaluation_interval": "1m",
            "tests": [{"interval": "1m",
                       "input_series": [
                           {"series": f'http_requests_total{{{BASE},status="200"}}', "values": f"0+{ok}x520"},
                           {"series": f'http_requests_total{{{BASE},status="500"}}', "values": f"0+{bad}x520"}],
                       "promql_expr_test": checks}]}
    (tmp_path / "tests.yml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    result = mlopskit.promtool("test", "rules", "tests.yml", cwd=tmp_path, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr


def test_ten_percent_errors_burn_fast_and_slow(tmp_path, rules_text):
    run(tmp_path, rules_text, 90, 10, [("ETAErrorBudgetFastBurn", "8h", True), ("ETAErrorBudgetSlowBurn", "8h", True)])


def test_five_percent_errors_only_burn_slowly(tmp_path, rules_text):
    run(tmp_path, rules_text, 95, 5, [("ETAErrorBudgetFastBurn", "8h", False), ("ETAErrorBudgetSlowBurn", "8h", True)])


def test_half_a_percent_of_errors_is_within_budget(tmp_path, rules_text):
    run(tmp_path, rules_text, 995, 5, [("ETAErrorBudgetFastBurn", "8h", False), ("ETAErrorBudgetSlowBurn", "8h", False)])


def test_no_traffic_burns_nothing(tmp_path, rules_text):
    run(tmp_path, rules_text, 0, 0, [("ETAErrorBudgetFastBurn", "8h", False), ("ETAErrorBudgetSlowBurn", "8h", False)])
