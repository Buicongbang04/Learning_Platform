import shutil
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import DockerLab, Exercise, ObsStack

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
APP = testkit.ROOT / "tracks" / "devops" / "sample-app"
RECORDS = ("job:http_requests:rate5m", "job:http_requests_errors:ratio_rate5m", "job_path:http_request_duration_seconds:p95_5m")
ALERTS = {"OlistApiHighErrorRate": "page", "OlistApiSlowOrders": "ticket"}
ALWAYS = {
    "OlistApiHighErrorRate": 'job:http_requests_errors:ratio_rate5m{job="olist-api"} >= 0',
    "OlistApiSlowOrders": 'job_path:http_request_duration_seconds:p95_5m{job="olist-api", path="/orders/{order_id}"} >= 0',
}


def load(name: str) -> dict:
    try:
        data = yaml.safe_load(ex.read(name))
    except yaml.YAMLError as error:
        pytest.fail(f"{name} không phải YAML hợp lệ: {error}")
    if not isinstance(data, dict):
        pytest.fail(f"{name} phải là một mapping YAML")
    return data


def rules_of(data: dict) -> list[dict]:
    return [rule for group in data.get("groups") or [] for rule in group.get("rules") or []]


def require_names(data: dict) -> None:
    rules = rules_of(data)
    records = [r.get("record") for r in rules if "record" in r]
    alerts = [r.get("alert") for r in rules if "alert" in r]
    missing = [n for n in RECORDS if n not in records] + [n for n in ALERTS if n not in alerts]
    assert not missing, f"rules.yml còn thiếu rule: {', '.join(missing)}"


def stage(tmp_path: Path, name: str, rules: dict, test_file: Path) -> Path:
    folder = tmp_path / name
    folder.mkdir()
    (folder / "rules.yml").write_text(yaml.safe_dump(rules, sort_keys=False, allow_unicode=True), encoding="utf-8")
    shutil.copy(test_file, folder / "tests.yml")
    return folder


def comparable(data: dict) -> dict:
    data = yaml.safe_load(yaml.safe_dump(data))
    for rule in rules_of(data):
        rule.pop("annotations", None)
        if "alert" in rule:
            rule["labels"] = {k: v for k, v in (rule.get("labels") or {}).items() if k == "severity"}
    return data


def mutate(data: dict, name: str, template: str) -> tuple[dict, str]:
    data = yaml.safe_load(yaml.safe_dump(data))
    expr = ""
    for rule in rules_of(data):
        if rule.get("record") == name or rule.get("alert") == name:
            expr = rule["expr"] = template.replace("{expr}", str(rule.get("expr", "")).strip())
    return data, expr


def test_rules_pass_promtool_check():
    require_names(load("rules.yml"))
    result = testkit.promtool("check", "rules", "rules.yml", cwd=ex.target)
    assert result.returncode == 0, result.stdout + result.stderr


def test_alert_labels_and_annotations():
    data = load("rules.yml")
    require_names(data)
    for rule in rules_of(data):
        name = rule.get("alert")
        if name not in ALERTS:
            continue
        assert (rule.get("labels") or {}).get("severity") == ALERTS[name], f"{name}: labels.severity phải là {ALERTS[name]}"
        annotations = rule.get("annotations") or {}
        assert str(annotations.get("summary") or "").strip(), f"{name}: cần annotations.summary"
        assert str(annotations.get("runbook_url") or "").startswith("https://"), f"{name}: runbook_url phải bắt đầu bằng https://"


def test_rules_behave_as_specified(tmp_path):
    data = load("rules.yml")
    require_names(data)
    folder = stage(tmp_path, "spec", comparable(data), FIXTURES / "semantics.test.yml")
    result = testkit.promtool("test", "rules", "tests.yml", cwd=folder)
    assert result.returncode == 0, "Rule chưa đúng đặc tả trong đề (kịch bản kiểm của bài):\n" + result.stdout + result.stderr


def test_own_unit_tests_pass_and_cover_every_rule():
    data = load("rules.test.yml")
    assert data.get("rule_files") == ["rules.yml"], "rules.test.yml phải có rule_files: [rules.yml]"
    tests = data.get("tests") or []
    exprs = " ".join(str(t.get("expr", "")) for case in tests for t in case.get("promql_expr_test") or [])
    missing = [name for name in RECORDS if name not in exprs]
    assert not missing, f"Chưa có promql_expr_test cho recording rule: {', '.join(missing)}"
    alert_tests = [t for case in tests for t in case.get("alert_rule_test") or []]
    for name in ALERTS:
        cases = [t for t in alert_tests if t.get("alertname") == name]
        assert any(t.get("exp_alerts") for t in cases), f"{name}: cần ít nhất một ca alert bắn"
        assert any(not t.get("exp_alerts") for t in cases), f"{name}: cần ít nhất một ca alert không bắn"
    result = testkit.promtool("test", "rules", "rules.test.yml", cwd=ex.target)
    assert result.returncode == 0, result.stdout + result.stderr


MUTANTS = [
    ("job:http_requests:rate5m", "({expr}) * 2", "rate-x2"),
    ("job:http_requests_errors:ratio_rate5m", "({expr}) / 2", "ratio-half"),
    ("job_path:http_request_duration_seconds:p95_5m", "({expr}) * 0.6", "p95-x0.6"),
    ("OlistApiHighErrorRate", "vector(1) == 0", "error-never"),
    ("OlistApiHighErrorRate", ALWAYS["OlistApiHighErrorRate"], "error-always"),
    ("OlistApiSlowOrders", "vector(1) == 0", "slow-never"),
    ("OlistApiSlowOrders", ALWAYS["OlistApiSlowOrders"], "slow-always"),
]


@pytest.mark.parametrize("name,template,case", MUTANTS, ids=[m[2] for m in MUTANTS])
def test_own_unit_tests_catch_broken_rule(tmp_path, name, template, case):
    data = load("rules.yml")
    require_names(data)
    load("rules.test.yml")
    mutant, expr = mutate(data, name, template)
    folder = stage(tmp_path, "mutant", mutant, ex.path("rules.test.yml"))
    result = testkit.promtool("test", "rules", "tests.yml", cwd=folder)
    assert result.returncode != 0, f"rules.test.yml vẫn pass khi {name} bị thay bằng `{expr}`: test của bạn chưa kiểm đủ chặt"


def olist_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(APP / "olist_shop", project / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(APP / "requirements.txt", project)
    shutil.copy(testkit.KUBE_OLIST_DOCKERFILE, project / "Dockerfile")
    shutil.copy(FIXTURES / "compose.yaml", project / "compose.yaml")
    rules = project / "observability" / "prometheus" / "rules"
    rules.mkdir(parents=True)
    shutil.copy(ex.path("rules.yml"), rules / "olist.yml")
    return project


def send_traffic(stack: ObsStack) -> None:
    import httpx

    api = f"http://127.0.0.1:{stack.project.port('api', 8000)}"
    stopped = stack.project.run("stop", "redis")
    assert stopped.returncode == 0, stopped.stderr
    with httpx.Client(trust_env=False, timeout=10) as client:
        for round in range(2):
            for i in range(10):
                client.get(f"{api}/orders/b01-{round}-{i}")
            for _ in range(3):
                assert client.get(f"{api}/readyz").status_code == 503
            if round == 0:
                seen = stack.prom_query('http_requests_total{job="olist-api", path="/readyz"}', timeout=30)
                assert seen, "Prometheus chưa scrape được api:8000"


def rule_health(stack: ObsStack) -> dict:
    import httpx

    with httpx.Client(trust_env=False, timeout=10) as client:
        groups = client.get(stack.url("prometheus") + "/api/v1/rules").json()["data"]["groups"]
    return {r["name"]: (r["health"], r.get("lastError", "")) for g in groups for r in g["rules"]}


def test_rules_on_real_olist_data(tmp_path):
    require_names(load("rules.yml"))
    for image in (testkit.KUBE_IMAGES["postgres"], testkit.KUBE_IMAGES["redis"], "python:3.12.16-slim-trixie"):
        ex.require_image(image)
    project = olist_project(tmp_path)
    with DockerLab() as lab:
        stack = ObsStack(lab, project=project)
        send_traffic(stack)
        health = stack.eventually(lambda: {k: v for k, v in rule_health(stack).items() if k in (*RECORDS, *ALERTS) and v[0] != "unknown"}, 30)
        bad = {k: v for k, v in health.items() if v[0] != "ok"}
        assert len(health) == len(RECORDS) + len(ALERTS) and not bad, f"Prometheus chưa nạp được rule: {bad or health}"
        checks = {
            "job:http_requests:rate5m": 'job:http_requests:rate5m{job="olist-api"} > 0',
            "job:http_requests_errors:ratio_rate5m": 'job:http_requests_errors:ratio_rate5m{job="olist-api"} > 0',
            "job_path:http_request_duration_seconds:p95_5m":
                'job_path:http_request_duration_seconds:p95_5m{job="olist-api", path="/orders/{order_id}"} >= 0',
        }
        empty = [name for name, expr in checks.items() if not stack.prom_query(expr, timeout=60)]
        assert not empty, ("Với metric thật của Olist Shop (hai đợt request /orders và /readyz trả 503), các recording "
                           f"rule sau không ra số nào: {', '.join(empty)}. So tên metric và tên label trong rule với /metrics thật")
