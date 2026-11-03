import re
import textwrap

import pytest
import yaml

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
BASE = 'job="eta-service",method="POST"'
DURATION = re.compile(r"^(\d+)([smh])$")


def seconds(text):
    match = DURATION.match(str(text))
    assert match, f"thời lượng không hợp lệ: {text!r}"
    return int(match.group(1)) * {"s": 1, "m": 60, "h": 3600}[match.group(2)]


@pytest.fixture(scope="module")
def rules_text():
    return ex.read("rules.yml")


@pytest.fixture(scope="module")
def alerts(rules_text):
    data = yaml.safe_load(rules_text)
    found = {}
    for group in data["groups"]:
        for rule in group.get("rules", []):
            if "alert" in rule:
                assert rule["alert"] not in found, f"trùng alert {rule['alert']}"
                found[rule["alert"]] = rule
    return found


def series(route, status, values):
    return f"http_requests_total{{{BASE},route=\"{route}\",status=\"{status}\"}}", values


def run_scenario(tmp_path, rules_text, input_series, expectations):
    names = {rule.get("alert") for group in yaml.safe_load(rules_text)["groups"] for rule in group.get("rules", [])}
    assert {"ETAHighErrorRate", "ETAMetricsAbsent"} <= names, "thiếu alert ETAHighErrorRate hoặc ETAMetricsAbsent"
    (tmp_path / "rules.yml").write_text(rules_text, encoding="utf-8")
    checks = []
    for alert, at, firing in expectations:
        checks.append({
            "expr": f'count(ALERTS{{alertname="{alert}",alertstate="firing"}})',
            "eval_time": at,
            "exp_samples": [{"labels": "{}", "value": 1}] if firing else [],
        })
    spec = {
        "rule_files": ["rules.yml"],
        "evaluation_interval": "1m",
        "tests": [{"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in input_series],
                   "promql_expr_test": checks}],
    }
    (tmp_path / "tests.yml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    result = mlopskit.promtool("test", "rules", "tests.yml", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_rules_file_is_valid_for_promtool(tmp_path, rules_text):
    (tmp_path / "rules.yml").write_text(rules_text, encoding="utf-8")
    result = mlopskit.promtool("check", "rules", "rules.yml", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_alert_metadata_is_complete(alerts):
    assert {"ETAHighErrorRate", "ETAMetricsAbsent"} <= set(alerts)
    error, absent = alerts["ETAHighErrorRate"], alerts["ETAMetricsAbsent"]
    assert error["labels"]["severity"] == "critical"
    assert absent["labels"]["severity"] == "warning"
    assert 180 <= seconds(error["for"]) <= 600
    assert 60 <= seconds(absent["for"]) <= 600
    for rule in (error, absent):
        assert rule["annotations"]["summary"].strip()
        assert str(rule["annotations"]["runbook_url"]).startswith("https://")


def test_sustained_errors_fire_after_the_for_period(tmp_path, rules_text):
    run_scenario(tmp_path, rules_text, [series("/predict", 200, "0+90x40"), series("/predict", 500, "0+10x40")], [
        ("ETAHighErrorRate", "2m", False),
        ("ETAHighErrorRate", "15m", True),
        ("ETAHighErrorRate", "30m", True),
        ("ETAMetricsAbsent", "30m", False),
    ])


def test_no_traffic_does_not_fire_error_alert(tmp_path, rules_text):
    run_scenario(tmp_path, rules_text, [series("/predict", 200, "0+0x40"), series("/predict", 500, "0+0x40")], [
        ("ETAHighErrorRate", "15m", False),
        ("ETAHighErrorRate", "30m", False),
        ("ETAMetricsAbsent", "30m", False),
    ])


def test_one_percent_errors_do_not_fire(tmp_path, rules_text):
    run_scenario(tmp_path, rules_text, [series("/predict", 200, "0+99x40"), series("/predict", 500, "0+1x40")], [
        ("ETAHighErrorRate", "15m", False),
        ("ETAHighErrorRate", "30m", False),
    ])


def test_errors_on_other_routes_do_not_fire(tmp_path, rules_text):
    run_scenario(tmp_path, rules_text, [
        series("/predict", 200, "0+90x40"),
        series("/health", 200, "0+10x40"),
        series("/health", 500, "0+50x40"),
    ], [("ETAHighErrorRate", "15m", False)])


def test_alert_resolves_after_recovery(tmp_path, rules_text):
    run_scenario(tmp_path, rules_text, [series("/predict", 200, "0+90x40"), series("/predict", 500, "0+10x10 100+0x30")], [
        ("ETAHighErrorRate", "12m", True),
        ("ETAHighErrorRate", "30m", False),
    ])


def test_missing_metrics_fire_absent_alert(tmp_path, rules_text):
    run_scenario(tmp_path, rules_text, [series("/predict", 200, "0+90x10 stale"), series("/predict", 500, "0+10x10 stale")], [
        ("ETAMetricsAbsent", "5m", False),
        ("ETAMetricsAbsent", "25m", True),
        ("ETAHighErrorRate", "25m", False),
    ])
