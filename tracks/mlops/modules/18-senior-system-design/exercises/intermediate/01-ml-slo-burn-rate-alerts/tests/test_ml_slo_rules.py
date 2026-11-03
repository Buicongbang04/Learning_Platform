import re

import pytest
import yaml

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
RULES = "ml_slo.rules.yml"
DURATION = re.compile(r"^(\d+)([smh])$")
QUALITY = 'eta_quality_checks_total{{job="eta-service",model="eta-v7",outcome="{}"}}'
FRESHNESS = 'eta_feature_last_success_timestamp_seconds{{job="feature-pipeline",feature_view="{}"}}'
ALERT_NAMES = {
    "ETAQualityBudgetFastBurn": ("critical", 0, 1800),
    "ETAQualityBudgetSlowBurn": ("warning", 0, 3600),
    "ETAQualityLabelsMissing": ("warning", 0, 3600),
    "ETAFeatureFreshnessFastBurn": ("critical", 0, 300),
}


def seconds(text):
    match = DURATION.match(str(text))
    assert match, f"thời lượng không hợp lệ: {text!r}"
    return int(match.group(1)) * {"s": 1, "m": 60, "h": 3600}[match.group(2)]


@pytest.fixture(scope="module")
def rules_text():
    return ex.read(RULES)


def rules_of(text):
    data = yaml.safe_load(text) or {}
    return [rule for group in data.get("groups") or [] for rule in group.get("rules") or []]


def counter(segments):
    values, total = [0], 0
    for per_step, steps in segments:
        for _ in range(steps):
            total += per_step
            values.append(total)
    return " ".join(str(v) for v in values)


def promtool_scenario(tmp_path, rules_text, interval, input_series, expectations):
    names = {r.get("alert") for r in rules_of(rules_text)}
    missing = sorted(set(ALERT_NAMES) - names)
    assert not missing, f"thiếu alert {missing}"
    (tmp_path / RULES).write_text(rules_text, encoding="utf-8")
    checks = [{"expr": f'count(ALERTS{{alertname="{name}",alertstate="firing"}})', "eval_time": at,
               "exp_samples": [{"labels": "{}", "value": 1}] if firing else []} for name, at, firing in expectations]
    spec = {"rule_files": [RULES], "evaluation_interval": "1m",
            "tests": [{"interval": interval,
                       "input_series": [{"series": s, "values": v} for s, v in input_series],
                       "promql_expr_test": checks}]}
    (tmp_path / "tests.yml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    result = mlopskit.promtool("test", "rules", "tests.yml", cwd=tmp_path, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr


def quality(good_segments, bad_segments):
    return [(QUALITY.format("good"), counter(good_segments)), (QUALITY.format("bad"), counter(bad_segments))]


def freshness(values):
    return [(FRESHNESS.format("trip_stats"), values), (FRESHNESS.format("zone_stats"), "0x200")]


def timestamps(stall_from=None, stall_to=None, minutes=200):
    out = []
    for minute in range(minutes + 1):
        if stall_from is not None and stall_from <= minute < stall_to:
            out.append(stall_from * 60)
        else:
            out.append(minute * 60)
    return " ".join(str(v) for v in out)


def test_rules_file_passes_promtool_check(tmp_path, rules_text):
    (tmp_path / RULES).write_text(rules_text, encoding="utf-8")
    result = mlopskit.promtool("check", "rules", RULES, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_alert_metadata(rules_text):
    alerts = {}
    for rule in rules_of(rules_text):
        if "alert" in rule:
            assert rule["alert"] not in alerts, f"trùng alert {rule['alert']}"
            alerts[rule["alert"]] = rule
    missing = sorted(set(ALERT_NAMES) - set(alerts))
    assert not missing, f"thiếu alert {missing}"
    for name, (severity, low, high) in ALERT_NAMES.items():
        rule = alerts[name]
        assert rule.get("labels", {}).get("severity") == severity, name
        assert low <= seconds(rule.get("for", "0s")) <= high, f"{name}: for ngoài khoảng cho phép"
        assert str(rule.get("annotations", {}).get("summary", "")).strip(), name
        assert str(rule.get("annotations", {}).get("runbook_url", "")).startswith("https://"), name
    for name in ("ETAQualityBudgetFastBurn", "ETAQualityBudgetSlowBurn", "ETAFeatureFreshnessFastBurn"):
        assert re.search(r"\band\b", alerts[name]["expr"]), f"{name}: cần hai cửa sổ nối bằng and"


def test_heavy_quality_loss_burns_fast_and_slow(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "5m", quality([(80, 432)], [(20, 432)]), [
        ("ETAQualityBudgetFastBurn", "12h", True),
        ("ETAQualityBudgetSlowBurn", "30h", True),
        ("ETAQualityLabelsMissing", "30h", False),
    ])


def test_moderate_quality_loss_only_burns_slowly(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "5m", quality([(92, 432)], [(8, 432)]), [
        ("ETAQualityBudgetFastBurn", "12h", False),
        ("ETAQualityBudgetFastBurn", "30h", False),
        ("ETAQualityBudgetSlowBurn", "30h", True),
    ])


def test_quality_within_budget_stays_quiet(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "5m", quality([(197, 432)], [(3, 432)]), [
        ("ETAQualityBudgetFastBurn", "30h", False),
        ("ETAQualityBudgetSlowBurn", "30h", False),
        ("ETAQualityLabelsMissing", "30h", False),
    ])


def test_fast_burn_resolves_soon_after_recovery(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "5m", quality([(80, 144), (100, 144)], [(20, 144), (0, 144)]), [
        ("ETAQualityBudgetFastBurn", "11h", True),
        ("ETAQualityBudgetFastBurn", "13h", False),
    ])


def test_label_series_vanishing_is_not_reported_as_green(tmp_path, rules_text):
    series = [(name, values + " stale") for name, values in quality([(197, 72)], [(3, 72)])]
    promtool_scenario(tmp_path, rules_text, "5m", series, [
        ("ETAQualityLabelsMissing", "3h", False),
        ("ETAQualityLabelsMissing", "14h", True),
        ("ETAQualityBudgetFastBurn", "14h", False),
    ])


def test_labels_stopping_is_not_reported_as_green(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "5m", quality([(197, 72), (0, 216)], [(3, 72), (0, 216)]), [
        ("ETAQualityLabelsMissing", "3h", False),
        ("ETAQualityLabelsMissing", "14h", True),
        ("ETAQualityBudgetFastBurn", "14h", False),
        ("ETAQualityBudgetSlowBurn", "14h", False),
    ])


def test_long_feature_stall_burns_freshness_budget(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "1m", freshness(timestamps(60, 100)), [
        ("ETAFeatureFreshnessFastBurn", "70m", False),
        ("ETAFeatureFreshnessFastBurn", "97m", True),
        ("ETAFeatureFreshnessFastBurn", "120m", False),
    ])


def test_short_feature_stall_does_not_page(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "1m", freshness(timestamps(60, 78)), [
        ("ETAFeatureFreshnessFastBurn", "78m", False),
        ("ETAFeatureFreshnessFastBurn", "85m", False),
    ])


def test_fresh_features_stay_quiet(tmp_path, rules_text):
    promtool_scenario(tmp_path, rules_text, "1m", freshness(timestamps()), [
        ("ETAFeatureFreshnessFastBurn", "60m", False),
        ("ETAFeatureFreshnessFastBurn", "180m", False),
    ])
