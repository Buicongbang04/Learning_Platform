import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
WINDOWS = ("5m", "30m", "1h", "2h", "6h", "1d", "3d")
ALERTS = {("page", "1h"): ("5m", 14.4), ("page", "6h"): ("30m", 6), ("ticket", "1d"): ("2h", 3), ("ticket", "3d"): ("6h", 1)}
SPEC = """service: olist-api
slos:
  - name: checkout
    objective: 99.9
    window: 30d
    errors: sum(rate(x_total{code="5xx"}[{{window}}]))
    total: sum(rate(x_total[{{window}}]))
"""


@pytest.fixture(scope="module")
def slogen():
    return ex.module("slogen.py")


def spec_of(slogen) -> dict:
    return slogen.load_spec(ex.path("slo.yaml"))


def rules_of(data: dict) -> list[dict]:
    return [rule for group in data["groups"] for rule in group["rules"]]


def stage(tmp_path: Path, rules: dict) -> Path:
    folder = tmp_path / "promtool"
    folder.mkdir()
    (folder / "rules.yml").write_text(yaml.safe_dump(rules, sort_keys=False, allow_unicode=True), encoding="utf-8")
    shutil.copy(FIXTURES / "slo.test.yml", folder / "tests.yml")
    return folder


def without_annotations(rules: dict) -> dict:
    data = yaml.safe_load(yaml.safe_dump(rules))
    for rule in rules_of(data):
        rule.pop("annotations", None)
    return data


def test_slo_file_targets(slogen):
    spec = spec_of(slogen)
    slos = {s["name"]: s for s in spec["slos"]}
    assert spec["service"] == "olist-api" and set(slos) == {"orders-availability", "orders-latency"}
    assert slos["orders-availability"]["objective"] == 99.5 and slos["orders-latency"]["objective"] == 95
    for slo in slos.values():
        for key in ("errors", "total"):
            assert 'job="olist-api"' in slo[key] and 'path="/orders/{order_id}"' in slo[key], f"{slo['name']}.{key}"
    assert 'le="0.25"' in slos["orders-latency"]["errors"]
    assert "5.." in slos["orders-availability"]["errors"]


BAD_SPECS = {
    "objective-100": SPEC.replace("objective: 99.9", "objective: 100"),
    "objective-text": SPEC.replace("objective: 99.9", 'objective: "99.9%"'),
    "window-7d": SPEC.replace("window: 30d", "window: 7d"),
    "no-placeholder": SPEC.replace("[{{window}}]))\n    total", "[5m]))\n    total"),
    "bad-name": SPEC.replace("name: checkout", "name: Checkout API"),
    "bad-service": SPEC.replace("service: olist-api", "service: 42"),
    "duplicate": SPEC + SPEC.split("slos:\n", 1)[1],
    "empty": "service: olist-api\nslos: []\n",
}


@pytest.mark.parametrize("case", BAD_SPECS)
def test_load_spec_rejects_bad_files(slogen, tmp_path, case):
    good = tmp_path / "good.yaml"
    good.write_text(SPEC, encoding="utf-8")
    assert slogen.load_spec(good)["slos"][0]["name"] == "checkout"
    bad = tmp_path / "bad.yaml"
    bad.write_text(BAD_SPECS[case], encoding="utf-8")
    with pytest.raises(ValueError):
        slogen.load_spec(bad)


def test_budget(slogen):
    assert slogen.budget({"objective": 99.5}) == pytest.approx(0.005)
    assert slogen.budget({"objective": 95}) == pytest.approx(0.05)
    assert slogen.budget({"objective": 99.95}) == pytest.approx(0.0005)


def test_recording_rules_cover_every_window(slogen):
    slo = spec_of(slogen)["slos"][0]
    rules = slogen.recording_rules(slo)
    assert [r["record"] for r in rules] == [f"slo:sli_error:ratio_rate{w}" for w in WINDOWS]
    for rule, window in zip(rules, WINDOWS):
        assert rule["labels"] == {"slo": slo["name"]}
        assert f"[{window}]" in rule["expr"] and "{{window}}" not in rule["expr"]
        assert rule["expr"].count(f"[{window}]") >= 2, "Cả tử số và mẫu số phải dùng cùng cửa sổ"


def test_alert_rules_long_and_short_window(slogen):
    for slo in spec_of(slogen)["slos"]:
        rules = slogen.alert_rules(slo)
        assert len(rules) == 4 and {r["alert"] for r in rules} == {"ErrorBudgetBurn"}
        seen = set()
        for rule in rules:
            key = (rule["labels"].get("severity"), rule["labels"].get("long_window"))
            assert key in ALERTS and set(rule["labels"]) == {"severity", "long_window"}, rule["labels"]
            seen.add(key)
            short, factor = ALERTS[key]
            expr = rule["expr"]
            assert f"slo:sli_error:ratio_rate{key[1]}" in expr and f"slo:sli_error:ratio_rate{short}" in expr
            assert re.search(r"\band\b", expr), "Cần cả cửa sổ dài VÀ cửa sổ ngắn"
            assert f'slo="{slo["name"]}"' in expr
            numbers = [float(n) for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?:e-?\d+)?(?![\w.])", expr)]
            expected = factor * (1 - slo["objective"] / 100)
            assert any(abs(n - expected) < 1e-9 for n in numbers) or (
                any(abs(n - factor) < 1e-9 for n in numbers) and any(abs(n - (1 - slo["objective"] / 100)) < 1e-9 for n in numbers)
            ), f"Ngưỡng của {key} phải là {factor} lần budget"
            assert rule["annotations"]["runbook_url"].startswith("https://") and slo["name"] in rule["annotations"]["runbook_url"]
            assert rule["annotations"].get("summary")
            assert "for" not in rule, "Cửa sổ ngắn đã làm nhiệm vụ chờ; không cần for"
        assert seen == set(ALERTS)


def test_generate_groups(slogen):
    rules = slogen.generate(spec_of(slogen))
    assert [g["name"] for g in rules["groups"]] == ["slo-orders-availability", "slo-orders-latency"]
    for group in rules["groups"]:
        assert len(group["rules"]) == len(WINDOWS) + len(ALERTS)


def test_generated_rules_pass_promtool_check(slogen, tmp_path):
    folder = stage(tmp_path, slogen.generate(spec_of(slogen)))
    result = testkit.promtool("check", "rules", "rules.yml", cwd=folder)
    assert result.returncode == 0, result.stdout + result.stderr


def test_burn_rate_scenarios(slogen, tmp_path):
    folder = stage(tmp_path, without_annotations(slogen.generate(spec_of(slogen))))
    result = testkit.promtool("test", "rules", "tests.yml", cwd=folder, timeout=300)
    assert result.returncode == 0, (result.stdout + result.stderr)[-4000:]


def test_cli_prints_same_rules(slogen, tmp_path):
    result = testkit.run_sandboxed([sys.executable, str(ex.path("slogen.py")), str(ex.path("slo.yaml"))], writable=[tmp_path],
                                   cwd=tmp_path, env={}, readonly=[ex.target])
    assert result.returncode == 0, result.stderr
    assert yaml.safe_load(result.stdout) == slogen.generate(spec_of(slogen))
