import importlib.util
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
ALERT = "ETAHighErrorRate"


def load_service():
    spec = importlib.util.spec_from_file_location("eta_app_fixture", FIXTURES / "eta_app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def real_series(good, error, unavailable):
    client = TestClient(load_service().create_app())
    for mode, count in (("ok", good), ("error", error), ("unavailable", unavailable)):
        for _ in range(count):
            client.post("/predict", json={"mode": mode})
    text = client.get("/metrics").text
    found = []
    for family in text_string_to_metric_families(text):
        for sample in family.samples:
            if sample.name == "http_requests_total":
                labels = dict(sample.labels, job="eta-service")
                selector = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                found.append((f"http_requests_total{{{selector}}}", int(sample.value)))
    return found


def run(tmp_path, rules_text, series, expectations):
    (tmp_path / "rules.yml").write_text(rules_text, encoding="utf-8")
    checks = [{"expr": f'count(ALERTS{{alertname="{ALERT}",alertstate="firing"}})', "eval_time": at,
               "exp_samples": [{"labels": "{}", "value": 1}] if firing else []} for at, firing in expectations]
    spec = {"rule_files": ["rules.yml"], "evaluation_interval": "1m",
            "tests": [{"interval": "1m", "input_series": [{"series": s, "values": f"0+{v}x40"} for s, v in series],
                       "promql_expr_test": checks}]}
    (tmp_path / "tests.yml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    result = mlopskit.promtool("test", "rules", "tests.yml", cwd=tmp_path)
    return result


def passes(tmp_path, rules_text, series, expectations):
    result = run(tmp_path, rules_text, series, expectations)
    assert result.returncode == 0, result.stdout + result.stderr


def test_regression_original_rule_stays_silent_while_service_really_errors(tmp_path):
    original = (FIXTURES / "rules.original.yml").read_text(encoding="utf-8")
    series = real_series(good=70, error=20, unavailable=10)
    assert sum(v for s, v in series if 'code="500"' in s or 'code="503"' in s) == 30
    passes(tmp_path, original, series, [("15m", False), ("30m", False)])


def test_rule_fires_when_the_service_really_errors(tmp_path):
    rules = ex.read("rules.yml")
    passes(tmp_path, rules, real_series(good=70, error=20, unavailable=10), [("2m", False), ("15m", True), ("30m", True)])


def test_rule_stays_quiet_when_service_is_healthy(tmp_path):
    rules = ex.read("rules.yml")
    passes(tmp_path, rules, real_series(good=100, error=0, unavailable=0), [("15m", False), ("30m", False)])


def test_rule_ignores_a_one_percent_error_rate(tmp_path):
    rules = ex.read("rules.yml")
    passes(tmp_path, rules, real_series(good=99, error=1, unavailable=0), [("15m", False), ("30m", False)])


def test_rule_stays_quiet_without_traffic(tmp_path):
    rules = ex.read("rules.yml")
    series = [(s, 0) for s, _ in real_series(good=1, error=1, unavailable=1)]
    passes(tmp_path, rules, series, [("15m", False), ("30m", False)])


def test_alert_definition_is_otherwise_unchanged():
    text = ex.read("rules.yml")
    mine = yaml.safe_load(text)["groups"][0]["rules"]
    original = yaml.safe_load((FIXTURES / "rules.original.yml").read_text(encoding="utf-8"))["groups"][0]["rules"]
    assert len(mine) == 1
    for key in ("alert", "for", "labels", "annotations"):
        assert mine[0][key] == original[0][key]
    assert "0.05" in mine[0]["expr"] and "[5m]" in mine[0]["expr"]
    assert 'route="/predict"' in mine[0]["expr"] and 'job="eta-service"' in mine[0]["expr"]


def test_rules_file_is_valid_for_promtool(tmp_path):
    (tmp_path / "rules.yml").write_text(ex.read("rules.yml"), encoding="utf-8")
    result = mlopskit.promtool("check", "rules", "rules.yml", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
