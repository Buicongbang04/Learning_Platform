import re

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
MATCHER = re.compile(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(=~|!~|!=|=)\s*"?(.*?)"?\s*$')
TOP_LEVEL = {"global", "route", "receivers", "inhibit_rules", "templates", "time_intervals", "mute_time_intervals"}


@pytest.fixture(scope="module")
def config():
    return yaml.safe_load(ex.read("alertmanager.yml"))


def seconds(text):
    match = re.fullmatch(r"(\d+)([smhd])", str(text))
    assert match, f"thời lượng không hợp lệ: {text!r}"
    return int(match.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]


def matches(matchers, labels):
    for text in matchers or []:
        parsed = MATCHER.match(text)
        assert parsed, f"matcher không hợp lệ: {text!r}"
        name, op, value = parsed.groups()
        actual = labels.get(name, "")
        if op == "=" and actual != value:
            return False
        if op == "!=" and actual == value:
            return False
        if op == "=~" and not re.fullmatch(value, actual):
            return False
        if op == "!~" and re.fullmatch(value, actual):
            return False
    return True


def receivers_for(route, labels):
    found = []
    for child in route.get("routes", []):
        if matches(child.get("matchers"), labels):
            found.extend(receivers_for(child, labels))
            if not child.get("continue", False):
                return found
    return found or [route["receiver"]]


def inhibited(config, alert, active):
    for rule in config.get("inhibit_rules", []):
        if not matches(rule.get("target_matchers"), alert):
            continue
        for source in active:
            if source is alert or not matches(rule.get("source_matchers"), source):
                continue
            if all(source.get(label) == alert.get(label) and label in alert for label in rule.get("equal", [])):
                return True
    return False


def all_routes(route):
    yield route
    for child in route.get("routes", []):
        yield from all_routes(child)


def alert(name, severity=None, **labels):
    result = {"alertname": name, **labels}
    if severity:
        result["severity"] = severity
    return result


def test_file_shape_and_receivers(config):
    assert set(config) <= TOP_LEVEL
    names = [r["name"] for r in config["receivers"]]
    assert len(names) == len(set(names))
    assert {"default", "oncall", "ticket"} <= set(names)
    assert config["route"]["receiver"] == "default"
    for route in all_routes(config["route"]):
        assert route["receiver"] in names
        assert "match" not in route and "match_re" not in route, "dùng matchers, không dùng match/match_re đã cũ"


def test_critical_goes_to_oncall_only(config):
    for labels in (alert("ETAHighErrorRate", "critical", service="eta"),
                   alert("ETAHighErrorRate", "critical", service="eta", team="ml"),
                   alert("DiskFull", "critical")):
        assert receivers_for(config["route"], labels) == ["oncall"]


def test_warning_goes_to_ticket_only(config):
    assert receivers_for(config["route"], alert("ETAMetricsAbsent", "warning", service="eta")) == ["ticket"]
    assert receivers_for(config["route"], alert("ETAHighLatency", "warning", service="eta", team="ml")) == ["ticket"]


def test_unknown_or_missing_severity_is_not_dropped(config):
    assert receivers_for(config["route"], alert("Whatever", "info")) == ["default"]
    assert receivers_for(config["route"], alert("NoSeverity")) == ["default"]
    assert receivers_for(config["route"], alert("Shouty", "Critical")) == ["default"]


def test_grouping(config):
    root = config["route"]
    assert {"alertname", "service"} <= set(root["group_by"])
    for route in all_routes(root):
        if "group_by" in route:
            assert "alertname" in route["group_by"]


def test_timings_page_fast_and_ticket_slowly(config):
    critical = next(r for r in config["route"]["routes"] if matches(r.get("matchers"), alert("x", "critical")))
    warning = next(r for r in config["route"]["routes"] if matches(r.get("matchers"), alert("x", "warning")))
    assert seconds(critical["group_wait"]) <= 30
    assert seconds(critical["repeat_interval"]) <= 4 * 3600
    assert seconds(warning["group_wait"]) >= 60
    assert seconds(warning["repeat_interval"]) >= 12 * 3600
    for route in (critical, warning):
        assert seconds(route["group_interval"]) >= 60
        assert seconds(route["repeat_interval"]) >= seconds(route["group_interval"])


def test_receivers_have_working_integrations(config):
    receivers = {r["name"]: r for r in config["receivers"]}
    for name in ("oncall", "ticket"):
        hooks = receivers[name].get("webhook_configs") or []
        assert hooks, f"{name} cần ít nhất một webhook_configs"
        assert all(re.match(r"^https?://", h["url"]) for h in hooks)
    assert all(h.get("send_resolved") is True for h in receivers["oncall"]["webhook_configs"])


def test_critical_inhibits_warning_of_same_service(config):
    page = alert("ETAHighErrorRate", "critical", service="eta")
    noise = alert("ETAHighLatency", "warning", service="eta")
    other = alert("ETAHighLatency", "warning", service="pricing")
    active = [page, noise, other]
    assert inhibited(config, noise, active) is True
    assert inhibited(config, other, active) is False
    assert inhibited(config, page, active) is False


def test_nothing_is_inhibited_without_a_critical(config):
    warning = alert("ETAHighLatency", "warning", service="eta")
    assert inhibited(config, warning, [warning, alert("ETAMetricsAbsent", "warning", service="eta")]) is False
    assert inhibited(config, alert("A", "critical", service="eta"), [warning]) is False


def test_inhibit_rule_needs_an_equal_clause(config):
    rules = config.get("inhibit_rules") or []
    assert rules
    assert all(rule.get("equal") for rule in rules), "inhibit không có equal sẽ tắt mọi warning của mọi service"
