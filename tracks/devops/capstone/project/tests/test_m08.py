"""M08: stack production của M03 cộng observability (`testkit.ObsStack`): metric RED của api và worker bằng recording rule,
log có trace_id trong Loki, trace có span DB trong Jaeger, dashboard Grafana provision, alert rule kèm promtool test, alert
bắn thật khi dừng worker. Hợp đồng đầy đủ ở capstone/milestones/m08-observability.md."""

import json
import re
import secrets
import shutil
import time
import uuid
from pathlib import Path

import httpx
import pytest
import yaml

from olist_stack import COMPOSE, DOCKERFILE, assemble, build_targets, missing
from testkit import DockerLab, Exercise, ObsStack, amtool, promtool

DOC = "m08-observability.md"
OBS = "observability"
RULES = "prometheus/rules/olist.yml"
RULE_TESTS = "prometheus/olist.test.yml"
ALERTMANAGER = "alertmanager/alertmanager.yml"
DASHBOARD = "grafana/dashboards/olist-shop.json"
FILES = (RULES, RULE_TESTS, ALERTMANAGER, DASHBOARD)
SEMANTICS = Path(__file__).parent / "fixtures" / "m08" / "semantics.test.yml"
RECORDS = ("olist:api_requests:rate1m", "olist:api_errors:ratio_rate1m", "olist:api_latency_seconds:p95_1m",
           "olist:worker_jobs:rate1m", "olist:worker_errors:ratio_rate1m", "olist:worker_duration_seconds:p95_1m")
ALERTS = {"OlistApiHighErrorRate": ("page", "api"), "OlistApiSlow": ("ticket", "api"), "OlistWorkerDown": ("page", "worker")}
ROUTES = {"page": "olist-page", "ticket": "olist-ticket"}
ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"
ENDPOINT_REF = re.compile(r"^\$\{OTEL_EXPORTER_OTLP_ENDPOINT(:?-)?\}$")
COLLECTOR = "http://otel-collector:4317"
TRACE_ID = re.compile(r'"trace_id":\s*"([0-9a-f]{32})"')
MACROS = ("$__rate_interval", "${__rate_interval}", "$__interval", "${__interval}", "$__range", "${__range}")
DATA_WAIT = 120
ALERT_WAIT = 150
RESOLVE_WAIT = 120


def obs_dir(project_root: Path) -> Path:
    return project_root / OBS


def missing_files(project_root: Path) -> list[str]:
    found = [missing(obs_dir(project_root) / name, DOC) for name in FILES if not (obs_dir(project_root) / name).is_file()]
    for rel, doc in ((COMPOSE, "m03-containers.md"), (DOCKERFILE, "m03-containers.md")):
        if not (project_root / rel).is_file():
            found.append(missing(project_root / rel, doc) + " (M08 dựng stack production của M03)")
    return found


def require_files(project_root: Path) -> Path:
    found = missing_files(project_root)
    if found:
        pytest.fail("\n".join(found), pytrace=False)
    return obs_dir(project_root)


def read_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}", pytrace=False)


def rule_slots(data) -> list[tuple[int, int, dict]]:
    """(chỉ số group, chỉ số rule, rule) cho mọi rule là mapping trong group là mapping; phần sai hình dạng bị bỏ qua."""
    groups = data.get("groups") if isinstance(data, dict) else None
    return [(gi, ri, rule) for gi, group in enumerate(groups if isinstance(groups, list) else []) if isinstance(group, dict)
            for ri, rule in enumerate(group.get("rules") if isinstance(group.get("rules"), list) else []) if isinstance(rule, dict)]


def rules_of(obs: Path) -> list[dict]:
    return [rule for _, _, rule in rule_slots(read_yaml(obs / RULES))]


def loaded_rules(obs: Path) -> dict:
    data = read_yaml(obs / RULES)
    if not rule_slots(data):
        pytest.fail(f"{RULES} phải có groups: [ {{name, rules: [...]}} ] với ít nhất một rule", pytrace=False)
    return data


def env_of(service: dict) -> dict:
    env = service.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) if "=" in item else (item, None) for item in env)
    return env if isinstance(env, dict) else {}


def compose_problems(project_root: Path) -> list[str]:
    data = read_yaml(project_root / COMPOSE) or {}
    services = data.get("services") if isinstance(data, dict) and isinstance(data.get("services"), dict) else {}
    found = []
    for name in ("api", "worker"):
        value = env_of(services.get(name) or {}).get(ENDPOINT_ENV)
        if not isinstance(value, str) or not ENDPOINT_REF.match(value.strip()):
            found.append(f"{COMPOSE}: service {name} đặt {ENDPOINT_ENV}: ${{{ENDPOINT_ENV}:-}} (lấy từ môi trường, rỗng thì tắt "
                         f"trace; không ghi cứng địa chỉ Collector), đang là {value!r}")
    clash = sorted(set(services) & {"otel-collector", "jaeger", "loki", "prometheus", "alertmanager", "grafana"})
    if clash:
        found.append(f"{COMPOSE}: không khai service {clash}: stack observability do testkit dựng (xem đề)")
    return found


def rule_problems(obs: Path) -> list[str]:
    rules = rules_of(obs)
    found = []
    records = {r.get("record") for r in rules if "record" in r}
    found += [f"Thiếu recording rule {name}" for name in RECORDS if name not in records]
    alerts = {r.get("alert"): r for r in rules if "alert" in r}
    for name, (severity, service) in ALERTS.items():
        rule = alerts.get(name)
        if rule is None:
            found.append(f"Thiếu alert {name}")
            continue
        labels = rule.get("labels") if isinstance(rule.get("labels"), dict) else {}
        if labels.get("severity") != severity or labels.get("service") != service:
            found.append(f"{name}: labels severity {severity}, service {service}, đang {labels}")
        annotations = rule.get("annotations") if isinstance(rule.get("annotations"), dict) else {}
        if not str(annotations.get("summary", "")).strip():
            found.append(f"{name}: cần annotations.summary (người trực đọc câu này đầu tiên)")
    return found


def stripped_rules(obs: Path, dest: Path) -> Path:
    """Bản chép tệp rule chỉ giữ nhãn severity, service và bỏ annotation, để kịch bản ẩn so đúng hành vi (promtool so
    annotation và nhãn từng chữ)."""
    data = loaded_rules(obs)
    for _, _, rule in rule_slots(data):
        if "alert" in rule:
            rule.pop("annotations", None)
            labels = rule.get("labels") if isinstance(rule.get("labels"), dict) else {}
            rule["labels"] = {k: v for k, v in labels.items() if k in ("severity", "service")}
    (dest / "rules").mkdir(parents=True, exist_ok=True)
    (dest / "rules" / "olist.yml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return dest


def coverage_problems(obs: Path) -> list[str]:
    data = read_yaml(obs / RULE_TESTS)
    tests = data.get("tests") if isinstance(data, dict) else None
    tests = [t for t in tests if isinstance(t, dict)] if isinstance(tests, list) else []
    firing, quiet, exprs = set(), set(), []

    def cases(test: dict, key: str) -> list[dict]:
        value = test.get(key)
        return [c for c in value if isinstance(c, dict)] if isinstance(value, list) else []

    for test in tests:
        for case in cases(test, "alert_rule_test"):
            (firing if case.get("exp_alerts") else quiet).add(case.get("alertname"))
        exprs += [str(case.get("expr", "")) for case in cases(test, "promql_expr_test") if case.get("exp_samples")]
    found = [f"{RULE_TESTS}: {name} cần ít nhất một ca bắn (exp_alerts khác rỗng)" for name in ALERTS if name not in firing]
    found += [f"{RULE_TESTS}: {name} cần ít nhất một ca không bắn (exp_alerts: [])" for name in ALERTS if name not in quiet]
    found += [f"{RULE_TESTS}: {name} cần một promql_expr_test có exp_samples" for name in RECORDS
              if not any(name in expr for expr in exprs)]
    return found


def mutants(obs: Path) -> dict[str, Path]:
    """Mỗi alert hai bản đột biến (không bao giờ bắn, luôn bắn), mỗi recording rule một bản nhân đôi giá trị; mỗi bản ở một thư
    mục riêng kèm tệp test của bạn."""
    variants = {}
    for group_index, rule_index, rule in rule_slots(read_yaml(obs / RULES)):
        if rule.get("alert") in ALERTS:
            variants[f"{rule['alert']} không bao giờ bắn"] = (group_index, rule_index, "vector(1) < 0")
            variants[f"{rule['alert']} luôn bắn"] = (group_index, rule_index, "vector(1)")
        elif rule.get("record") in RECORDS:
            variants[f"{rule['record']} nhân đôi"] = (group_index, rule_index, f"({rule.get('expr')}) * 2")
    return variants


def mutation_survivors(obs: Path, work: Path) -> tuple[list[str], int]:
    """Chạy tệp test của bạn trên từng bản đột biến (mỗi bản một lần promtool); trả các bản mà test vẫn pass và số bản đã chạy."""
    base = loaded_rules(obs)
    tests_text = (obs / RULE_TESTS).read_text(encoding="utf-8")
    survivors, variants = [], mutants(obs)
    for index, (label, (group_index, rule_index, expr)) in enumerate(variants.items()):
        data = json.loads(json.dumps(base))
        data["groups"][group_index]["rules"][rule_index]["expr"] = expr
        folder = work / f"m{index:02d}"
        (folder / "rules").mkdir(parents=True)
        (folder / "rules" / "olist.yml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        (folder / "olist.test.yml").write_text(tests_text, encoding="utf-8")
        if promtool("test", "rules", "olist.test.yml", cwd=folder).returncode == 0:
            survivors.append(label)
    return survivors, len(variants)


def dashboard_of(obs: Path) -> dict:
    try:
        data = json.loads((obs / DASHBOARD).read_text(encoding="utf-8"))
    except ValueError as error:
        pytest.fail(f"{DASHBOARD} không phải JSON hợp lệ: {error}", pytrace=False)
    return data if isinstance(data, dict) else {}


def panels_of(dashboard: dict) -> list[dict]:
    out = []
    for panel in dashboard.get("panels") if isinstance(dashboard.get("panels"), list) else []:
        if isinstance(panel, dict):
            out.append(panel)
            out += [p for p in panel.get("panels") if isinstance(p, dict)] if isinstance(panel.get("panels"), list) else []
    return out


def targets_of(panel: dict) -> list[dict]:
    targets = panel.get("targets")
    return [t for t in targets if isinstance(t, dict)] if isinstance(targets, list) else []


def datasource_uid(panel: dict, target: dict) -> str:
    source = target.get("datasource") or panel.get("datasource") or {}
    return str(source.get("uid", "")) if isinstance(source, dict) else str(source)


def prom_targets(dashboard: dict) -> list[str]:
    return [str(t.get("expr", "")) for p in panels_of(dashboard) for t in targets_of(p)
            if isinstance(t, dict) and datasource_uid(p, t) == "prometheus" and t.get("expr")]


def dashboard_problems(dashboard: dict) -> list[str]:
    found = []
    if dashboard.get("uid") != "olist-shop" or "Olist Shop" not in str(dashboard.get("title", "")):
        found.append(f"Dashboard uid olist-shop, title có chữ 'Olist Shop': uid {dashboard.get('uid')!r}")
    panels = panels_of(dashboard)
    sources = {datasource_uid(p, t) for p in panels for t in targets_of(p)}
    if any("${" in s or s.startswith("$") for s in sources):
        found.append(f"Datasource ghi bằng uid đã provision (prometheus, loki), không dùng biến {sorted(sources)}")
    exprs = prom_targets(dashboard)
    found += [f"Không panel Prometheus nào vẽ {name}" for name in RECORDS if not any(name in e for e in exprs)]
    if any(re.search(r"\$(?!__)\w|\$\{(?!__)", e) for e in exprs):
        found.append("Query Prometheus của panel không dùng biến dashboard (chỉ macro $__rate_interval, $__interval, $__range)")
    if not any(p.get("type") == "logs" and any(datasource_uid(p, t) == "loki" for t in targets_of(p)) for p in panels):
        found.append("Cần một panel kiểu logs đọc từ datasource loki")
    return found


def routed(config_dir: Path, *labels: str) -> str:
    result = amtool("config", "routes", "test", f"--config.file={Path(ALERTMANAGER).name}", *labels, cwd=config_dir)
    return result.stdout.strip() if result.returncode == 0 else f"lỗi: {(result.stderr or result.stdout).strip()[-300:]}"


def test_m08_compose_exports_telemetry(project_root):
    require_files(project_root)
    found = compose_problems(project_root)
    assert not found, "\n".join(found)


def test_m08_rules_valid_and_complete(project_root):
    obs = require_files(project_root)
    result = promtool("check", "rules", RULES, cwd=obs)
    assert result.returncode == 0, f"promtool check rules {RULES}:\n{(result.stdout + result.stderr)[-1500:]}"
    found = rule_problems(obs)
    assert not found, "\n".join(found)


def test_m08_rules_match_contract(project_root, tmp_path):
    obs = require_files(project_root)
    work = stripped_rules(obs, tmp_path / "semantics")
    shutil.copyfile(SEMANTICS, work / "semantics.test.yml")
    result = promtool("test", "rules", "semantics.test.yml", cwd=work)
    assert result.returncode == 0, (
        "Rule chưa đúng định nghĩa RED, ngưỡng và for trong đề (kịch bản của test, annotation bỏ qua):\n"
        f"{(result.stdout + result.stderr)[-2500:]}")


def test_m08_rule_tests_pass_and_cover(project_root):
    obs = require_files(project_root)
    result = promtool("test", "rules", Path(RULE_TESTS).name, cwd=obs / "prometheus")
    assert result.returncode == 0, f"promtool test rules {RULE_TESTS}:\n{(result.stdout + result.stderr)[-2000:]}"
    found = coverage_problems(obs)
    assert not found, "\n".join(found)


def test_m08_rule_tests_catch_mutants(project_root, tmp_path):
    obs = require_files(project_root)
    survivors, count = mutation_survivors(obs, tmp_path)
    assert count == len(ALERTS) * 2 + len(RECORDS), f"Không tạo đủ bản đột biến từ {RULES} (thiếu rule?): {count}"
    assert not survivors, f"Test của bạn vẫn pass khi rule bị sửa sai: {survivors}"


def test_m08_alertmanager_routes(project_root):
    obs = require_files(project_root)
    folder = obs / Path(ALERTMANAGER).parent
    check = amtool("check-config", Path(ALERTMANAGER).name, cwd=folder)
    assert check.returncode == 0, f"amtool check-config:\n{(check.stdout + check.stderr)[-1500:]}"
    found = []
    for alert, (severity, service) in ALERTS.items():
        got = routed(folder, f"alertname={alert}", f"severity={severity}", f"service={service}")
        if got != ROUTES[severity]:
            found.append(f"{alert} (severity={severity}) phải tới đúng receiver {ROUTES[severity]}, đang tới {got!r}")
    for labels in (("alertname=Watchdog", "severity=none"), ("alertname=Lạ", "severity=Page"), ("alertname=Lạ",)):
        got = routed(folder, *labels)
        if got in ROUTES.values() or got.startswith("lỗi") or "," in got:
            found.append(f"{' '.join(labels)} không được tới receiver page/ticket, đang tới {got!r}")
    assert not found, "\n".join(found)


def test_m08_dashboard_as_code(project_root):
    obs = require_files(project_root)
    found = dashboard_problems(dashboard_of(obs))
    assert not found, "\n".join(found)


class Observed:
    def __init__(self) -> None:
        self.error = ""
        self.failure = ""
        self.steps: dict[str, dict] = {}

    def step(self, name: str) -> dict:
        if self.error:
            pytest.fail(self.error, pytrace=False)
        if name not in self.steps:
            pytest.fail(f"Chưa tới bước {name}: {self.failure or 'bước trước lỗi'}", pytrace=False)
        return self.steps[name]


def stage(dest: Path, root: Path, project_root: Path) -> Path:
    """Project cho ObsStack: compose production M03 của bạn làm `compose.yaml`, cộng `observability/` của bạn đè lên cấu hình
    mặc định của stack."""
    dest.mkdir(parents=True)
    shutil.copyfile(root / COMPOSE, dest / "compose.yaml")
    shutil.copytree(obs_dir(project_root), dest / OBS, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def traffic(client: httpx.Client, api: str, rounds: int = 12) -> list[str]:
    jobs = []
    for index in range(rounds):
        client.get(f"{api}/healthz")
        client.get(f"{api}/orders/m08-{uuid.uuid4().hex[:12]}")
        client.get(f"{api}/stats/revenue-by-state")
        if index % 3 == 0:
            answer = client.post(f"{api}/jobs/recompute", headers={"X-Request-ID": f"m08-job-{index}"})
            if answer.status_code == 202:
                jobs.append(answer.json().get("job_id"))
        time.sleep(1.5)
    return jobs


def log_lines(stack: ObsStack, query: str, timeout: float = 60) -> list[str]:
    return [value for stream in stack.loki_query(query, timeout=timeout) for _, value in stream.get("values") or []]


def trace_step(stack: ObsStack, client: httpx.Client, api: str) -> dict:
    rid = f"m08-{uuid.uuid4().hex[:16]}"
    status = client.get(f"{api}/orders/khong-co-{rid}", headers={"X-Request-ID": rid}).status_code
    lines = [line for line in log_lines(stack, f'{{service_name="olist-shop-api"}} |= "{rid}"') if rid in line]
    found = [m.group(1) for line in lines for m in [TRACE_ID.search(line)] if m]
    trace_id = found[0] if found else ""
    traces = stack.eventually(lambda: [t for t in stack.jaeger_traces("olist-shop-api") if t["traceID"] == trace_id], 60) \
        if trace_id else []
    return {"rid": rid, "status": status, "lines": lines, "trace_id": trace_id, "spans": traces[0]["spans"] if traces else []}


def job_step(stack: ObsStack, client: httpx.Client, api: str) -> dict:
    rid = f"m08-job-{uuid.uuid4().hex[:12]}"
    answer = client.post(f"{api}/jobs/recompute", headers={"X-Request-ID": rid})
    job_id = answer.json().get("job_id") if answer.status_code == 202 else ""
    api_lines = [line for line in log_lines(stack, f'{{service_name="olist-shop-api"}} |= "{rid}"') if rid in line]
    found = [m.group(1) for line in api_lines for m in [TRACE_ID.search(line)] if m]
    trace_id = found[0] if found else ""
    worker = []
    if trace_id:
        query = f'{{service_name="olist-shop-worker"}} |= "{trace_id}" |= "job done"'
        worker = [line for line in log_lines(stack, query) if trace_id in line and "job done" in line]
    return {"status": answer.status_code, "job_id": job_id, "trace_id": trace_id, "worker": worker}


def red_step(stack: ObsStack) -> dict:
    return {name: stack.prom_query(name, timeout=DATA_WAIT) for name in RECORDS}


def peak_step(stack: ObsStack) -> dict:
    """Giá trị lớn nhất trong 5 phút của hai rule đếm: lúc test hỏi, traffic có thể đã dừng quá một phút và rate về 0."""
    return {name: stack.prom_query(f"max_over_time({name}[5m])", timeout=30)
            for name in ("olist:api_requests:rate1m", "olist:worker_jobs:rate1m")}


def rules_step(stack: ObsStack) -> list[dict]:
    with httpx.Client(trust_env=False, timeout=10) as client:
        groups = client.get(stack.url("prometheus") + "/api/v1/rules").json()["data"]["groups"]
    return [{"name": r.get("name"), "health": r.get("health"), "error": r.get("lastError", "")}
            for g in groups for r in g.get("rules") or []]


def dashboard_step(stack: ObsStack) -> dict:
    found = [d for d in stack.grafana_dashboards() if d.get("uid") == "olist-shop"]
    if not found:
        return {"provisioned": False, "queries": {}}
    dashboard = stack.grafana_dashboard("olist-shop")
    queries = {}
    for expr in prom_targets(dashboard):
        query = expr
        for macro in MACROS:
            query = query.replace(macro, "1m")
        queries[expr] = len(stack.prom_query(query, timeout=60))
    return {"provisioned": True, "queries": queries, "panels": len(panels_of(dashboard))}


def firing(stack: ObsStack, name: str) -> list:
    return stack.prom_query(f'ALERTS{{alertname="{name}", alertstate="firing"}}')


def alert_step(stack: ObsStack) -> dict:
    before = firing(stack, "OlistWorkerDown")
    stopped = stack.project.run("stop", "worker", timeout=120)
    start = time.monotonic()
    fired = stack.eventually(lambda: [a for a in stack.alerts() if (a.get("labels") or {}).get("alertname") == "OlistWorkerDown"
                                      and (a.get("status") or {}).get("state") == "active"], ALERT_WAIT, interval=3)
    seconds = time.monotonic() - start
    started = stack.project.run("start", "worker", timeout=120)
    deadline = time.monotonic() + RESOLVE_WAIT
    still = firing(stack, "OlistWorkerDown")
    while still and time.monotonic() < deadline:
        time.sleep(3)
        still = firing(stack, "OlistWorkerDown")
    return {"before": before, "stopped": stopped.returncode, "fired": fired or [], "seconds": seconds,
            "started": started.returncode, "still": still}


@pytest.fixture(scope="module")
def observed(project_root, tmp_path_factory):
    state = Observed()
    found = missing_files(project_root)
    if not found:
        try:
            found = compose_problems(project_root)
        except pytest.fail.Exception as error:
            found = [str(error)]
    if found:
        state.error = "Không dựng stack: " + "\n".join(found)
        yield state
        return
    Exercise.require_tool("docker")
    tmp = tmp_path_factory.mktemp("m08")
    root = assemble(tmp / "repo", project_root)
    version = f"m08-{uuid.uuid4().hex[:8]}"
    with DockerLab() as lab:
        try:
            tags = build_targets(lab, root, {"APP_VERSION": version, "GIT_COMMIT": uuid.uuid4().hex + uuid.uuid4().hex[:8]})
            env = {"OLIST_API_IMAGE": tags["api"], "OLIST_WORKER_IMAGE": tags["worker"], "POSTGRES_PASSWORD": secrets.token_hex(12),
                   ENDPOINT_ENV: COLLECTOR}
            stack = ObsStack(lab, project=stage(tmp / "stage", root, project_root), env=env)
            api = f"http://127.0.0.1:{stack.project.port('api', 8000)}"
            with httpx.Client(trust_env=False, timeout=10) as client:
                ready = stack.eventually(lambda: client.get(f"{api}/readyz").status_code == 200, 60)
                if not ready:
                    pytest.fail(f"/readyz của api chưa 200 sau 60 giây:\n{stack.project.logs(tail=20)[-2000:]}", pytrace=False)
                state.steps["trace"] = trace_step(stack, client, api)
                state.steps["job"] = job_step(stack, client, api)
                state.steps["traffic"] = {"jobs": traffic(client, api)}
            state.steps["red"] = red_step(stack)
            state.steps["peak"] = peak_step(stack)
            state.steps["rules"] = {"rules": rules_step(stack)}
            state.steps["dashboard"] = dashboard_step(stack)
            state.steps["alert"] = alert_step(stack)
        except (pytest.fail.Exception, AssertionError, httpx.HTTPError, KeyError, ValueError) as error:
            state.failure = f"{type(error).__name__}: {error}"
        yield state


def test_m08_logs_carry_trace_id(observed):
    step = observed.step("trace")
    assert step["lines"], f"Loki không có log của olist-shop-api chứa request id {step['rid']} (OTLP log tới Collector?)"
    assert step["trace_id"], f"Log của request {step['rid']} trong Loki không có trace_id 32 ký tự hex: {step['lines'][:2]}"
    job = observed.step("job")
    assert job["status"] == 202 and job["trace_id"], f"POST /jobs/recompute phải 202 và log của api có trace_id: {job}"
    assert job["worker"], (f"Loki không có log 'job done' của olist-shop-worker mang cùng trace_id {job['trace_id']} với request "
                           "đẩy job (context đi qua Redis)")


def test_m08_trace_has_db_span(observed):
    step = observed.step("trace")
    assert step["spans"], f"Jaeger không có trace {step['trace_id'] or '(chưa có trace_id)'} của olist-shop-api"
    server = [s for s in step["spans"] if s["service"] == "olist-shop-api" and s["parentSpanID"] is None]
    db = [s for s in step["spans"] if s["attributes"].get("db.system.name") == "postgresql"]
    assert server and any(s["parentSpanID"] == server[0]["spanID"] for s in db), (
        f"Trace phải có span HTTP gốc của api và ít nhất một span DB (db.system.name postgresql) là con trực tiếp của nó: "
        f"{[(s['name'], s['parentSpanID']) for s in step['spans']]}")


def test_m08_red_metrics_recorded(observed):
    step = observed.step("red")
    empty = [name for name, result in step.items() if not result]
    assert not empty, f"Recording rule không có dữ liệu sau traffic thật ({DATA_WAIT}s): {empty}"
    shapes = {name: [r.get("metric", {}) for r in result] for name, result in step.items()}
    wrong = {name: metrics for name, metrics in shapes.items() if metrics != [{"__name__": name}]}
    assert not wrong, f"Mỗi recording rule ra đúng một series chỉ có __name__: {wrong}"
    peak = observed.step("peak")
    for name, result in peak.items():
        value = float(result[0]["value"][1]) if result else 0.0
        assert value > 0, f"max_over_time({name}[5m]) phải lớn hơn 0 sau khi có request và job: {value}"


def test_m08_rules_loaded_in_prometheus(observed):
    rules = observed.step("rules")["rules"]
    names = {r["name"] for r in rules}
    absent = [name for name in (*RECORDS, *ALERTS) if name not in names]
    assert not absent, f"Prometheus của stack chưa nạp {absent} (tệp phải nằm ở observability/{RULES})"
    unhealthy = [f"{r['name']}: {r['error']}" for r in rules if r["health"] != "ok"]
    assert not unhealthy, f"Rule lỗi khi chạy trên Prometheus thật: {unhealthy}"


def test_m08_dashboard_provisioned_with_data(observed):
    step = observed.step("dashboard")
    assert step["provisioned"], "Grafana chưa provision dashboard uid olist-shop (tệp ở observability/grafana/dashboards/)"
    empty = [expr for expr, count in step["queries"].items() if not count]
    assert step["queries"] and not empty, f"Query của panel không trả dữ liệu trên stack thật: {empty or 'không có query'}"


def test_m08_worker_down_alert_fires(observed):
    step = observed.step("alert")
    assert not step["before"], "OlistWorkerDown đã firing khi worker còn chạy"
    assert step["stopped"] == 0, "docker compose stop worker lỗi"
    assert step["fired"], f"Alertmanager không nhận OlistWorkerDown trong {ALERT_WAIT}s sau khi dừng worker"
    receivers = {r.get("name") for a in step["fired"] for r in a.get("receivers") or []}
    assert receivers == {"olist-page"}, f"OlistWorkerDown phải tới receiver olist-page: {sorted(receivers)}"
    assert step["started"] == 0 and not step["still"], f"Chạy lại worker thì OlistWorkerDown phải hết firing trong {RESOLVE_WAIT}s"


def test_m08_checks_catch_bad_config(tmp_path):
    """Bộ kiểm tĩnh bắt được compose ghi cứng Collector, dashboard dùng biến datasource, test không phủ alert."""
    project = tmp_path / "p"
    (project / "container").mkdir(parents=True)
    (project / COMPOSE).write_text(yaml.safe_dump({"services": {
        "api": {"environment": {ENDPOINT_ENV: COLLECTOR}}, "worker": {"environment": [f"{ENDPOINT_ENV}=${{{ENDPOINT_ENV}:-}}"]},
        "grafana": {"image": "x"}}}), encoding="utf-8")
    found = compose_problems(project)
    assert len(found) == 2 and "service api" in found[0] and "grafana" in found[1], found
    bad = {"uid": "x", "panels": [{"type": "row", "panels": [{"type": "timeseries", "datasource": {"uid": "${DS_PROM}"},
                                                             "targets": [{"expr": "rate(x[$window])"}]}]}]}
    found = dashboard_problems(bad)
    assert any("uid olist-shop" in f for f in found) and any("biến" in f for f in found) and any("logs" in f for f in found), found
    assert len(panels_of(bad)) == 2
    assert panels_of({"panels": 3}) == [] and prom_targets({"panels": [{"targets": "x"}, {"targets": [1]}]}) == []
    assert any("uid olist-shop" in f for f in dashboard_problems({"panels": [{"type": "logs", "targets": "x"}]}))
    obs = tmp_path / "obs"
    (obs / "prometheus").mkdir(parents=True)
    (obs / RULE_TESTS).write_text(yaml.safe_dump({"tests": [{"alert_rule_test": [
        {"alertname": "OlistWorkerDown", "eval_time": "1m", "exp_alerts": [{"exp_labels": {"severity": "page"}}]}]}]}),
        encoding="utf-8")
    found = coverage_problems(obs)
    assert any("OlistWorkerDown cần ít nhất một ca không bắn" in f for f in found)
    assert not any("OlistWorkerDown cần ít nhất một ca bắn" in f for f in found)
    (obs / RULE_TESTS).write_text("tests:\n  - alert_rule_test: x\n    promql_expr_test: [1, {expr: y}]\n  - 3\n", encoding="utf-8")
    assert len(coverage_problems(obs)) == len(ALERTS) * 2 + len(RECORDS)
    (obs / RULES).parent.mkdir(parents=True)
    (obs / RULES).write_text("groups:\n  - x\n  - {name: g, rules: [1, {alert: OlistApiSlow, expr: up, labels: [a]}]}\n",
                             encoding="utf-8")
    assert rules_of(obs) == [{"alert": "OlistApiSlow", "expr": "up", "labels": ["a"]}]
    assert list(mutants(obs).values()) == [(1, 1, "vector(1) < 0"), (1, 1, "vector(1)")]
    stripped = yaml.safe_load((stripped_rules(obs, tmp_path / "s") / "rules" / "olist.yml").read_text(encoding="utf-8"))
    assert stripped["groups"][1]["rules"][1]["labels"] == {}
    (obs / RULES).write_text("groups: 3\n", encoding="utf-8")
    with pytest.raises(pytest.fail.Exception, match="groups"):
        stripped_rules(obs, tmp_path / "t")
    assert mutants(obs) == {}
