import re

import pytest
import yaml

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
TOP_LEVEL = {"global", "route", "receivers", "inhibit_rules", "templates", "time_intervals", "mute_time_intervals"}


@pytest.fixture(scope="module")
def text():
    return ex.read("alertmanager.yml")


@pytest.fixture(scope="module")
def config(text):
    return yaml.safe_load(text)


def seconds(text):
    match = re.fullmatch(r"(\d+)([smhd])", str(text))
    assert match, f"thời lượng không hợp lệ: {text!r}"
    return int(match.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]


def receivers_for(tmp_path, config_text, *labels):
    (tmp_path / "am.yml").write_text(config_text, encoding="utf-8")
    result = mlopskit.amtool("config", "routes", "test", "--config.file=am.yml", *labels, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    return [r for r in re.split(r"[,\s]+", result.stdout.strip()) if r]


def selects(matchers, severity):
    return any(re.fullmatch(rf'severity\s*=\s*"?{severity}"?', m.strip()) for m in matchers or [])


def all_routes(route):
    yield route
    for child in route.get("routes", []):
        yield from all_routes(child)


def test_file_shape_and_receivers(config):
    assert set(config) <= TOP_LEVEL
    names = [r["name"] for r in config["receivers"]]
    assert len(names) == len(set(names))
    assert {"default", "oncall", "ticket"} <= set(names)
    assert config["route"]["receiver"] == "default"
    for route in all_routes(config["route"]):
        assert route["receiver"] in names
        assert "match" not in route and "match_re" not in route, "dùng matchers, không dùng match/match_re đã cũ"


def test_amtool_accepts_the_config(tmp_path, text):
    (tmp_path / "am.yml").write_text(text, encoding="utf-8")
    result = mlopskit.amtool("check-config", "am.yml", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_critical_goes_to_oncall_only(tmp_path, text):
    for labels in (["severity=critical", "service=eta"], ["severity=critical", "service=eta", "team=ml"], ["severity=critical"]):
        assert receivers_for(tmp_path, text, *labels) == ["oncall"]


def test_warning_goes_to_ticket_only(tmp_path, text):
    assert receivers_for(tmp_path, text, "severity=warning", "service=eta") == ["ticket"]
    assert receivers_for(tmp_path, text, "severity=warning", "service=eta", "team=ml") == ["ticket"]


def test_unknown_or_missing_severity_is_not_dropped(tmp_path, text):
    assert receivers_for(tmp_path, text, "severity=info") == ["default"]
    assert receivers_for(tmp_path, text, "alertname=NoSeverity") == ["default"]
    assert receivers_for(tmp_path, text, "severity=Critical") == ["default"]


def test_grouping(config):
    root = config["route"]
    assert {"alertname", "service"} <= set(root["group_by"])
    for route in all_routes(root):
        if "group_by" in route:
            assert "alertname" in route["group_by"]


def test_timings_page_fast_and_ticket_slowly(config):
    critical = next(r for r in config["route"]["routes"] if selects(r.get("matchers"), "critical"))
    warning = next(r for r in config["route"]["routes"] if selects(r.get("matchers"), "warning"))
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


def test_inhibit_rule_shape(config):
    rules = config.get("inhibit_rules") or []
    assert rules
    for rule in rules:
        assert rule.get("equal"), "inhibit không có equal sẽ tắt mọi warning của mọi service"
    assert any(selects(r.get("source_matchers"), "critical") and selects(r.get("target_matchers"), "warning")
               and "service" in r["equal"] for r in rules)
