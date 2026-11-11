"""M09: đánh giá độc lập. Test chỉ chấm phần chấm được: SLO và burn-rate rule (promtool, kịch bản sinh theo objective của bạn),
runbook đủ mục, và game day trên stack M08 của bạn: hệ thống khôi phục sau một lỗi do `testkit.FaultInjector` bơm với seed lấy từ
thời gian chạy. Game day và postmortem tự chấm theo rubric. Hợp đồng đầy đủ ở capstone/milestones/m09-game-day.md."""

import os
import re
import secrets
import shutil
import subprocess
import threading
import time
import uuid
import warnings
from pathlib import Path

import httpx
import pytest
import yaml

from olist_stack import COMPOSE, DOCKERFILE, assemble, build_targets, missing
from testkit import FAULT_NETEM_BUILD, FAULT_NETEM_IMAGE, DockerLab, Exercise, FaultInjector, ObsStack, amtool, promtool

DOC = "m09-game-day.md"
SLO_FILE = "sre/slo.yaml"
RUNBOOK_YAML = "sre/runbook.yaml"
RUNBOOK_MD = "sre/RUNBOOK.md"
OBS = "observability"
SLO_RULES = "prometheus/rules/slo.yml"
SLO_TESTS = "prometheus/slo.test.yml"
ALERTMANAGER = "alertmanager/alertmanager.yml"
SLO_NAME = "api-availability"
OBJECTIVE_MIN, OBJECTIVE_MAX = 99.0, 99.95
WINDOWS = ("5m", "30m", "1h", "2h", "6h", "1d")
RECORDS = tuple(f"olist:slo_api_errors:ratio_rate{w}" for w in WINDOWS)
BURN = "OlistApiErrorBudgetBurn"
TIERS = (("page", "1h"), ("page", "6h"), ("ticket", "1d"))
ROUTES = {"page": "olist-page", "ticket": "olist-ticket"}
MAX_FOR = 120
DURATION = re.compile(r"(\d+)(ms|s|m|h|d|w|y)")
UNITS = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}
ID = re.compile(r"[a-z0-9]([-a-z0-9]{0,40}[a-z0-9])?")
ANCHOR = re.compile(r"(?:^|/)RUNBOOK\.md#([a-z0-9-]+)$")
ACTIONS = ("start", "restart", "recreate")
SERVICES = ("api", "worker", "postgres", "redis")
SECTIONS = ("Triệu chứng", "Tác động", "Chẩn đoán", "Khôi phục", "Xác nhận", "Leo thang")
ENTRIES_MIN, ENTRIES_MAX = 4, 12
SEED_ENV = "M09_SEED"
FAULTS = ("kill", "net-delay", "redis-stop")
FAULT_SERVICES = ("api", "postgres", "redis")
DELAY_MS = 800
COLLECTOR = "http://otel-collector:4317"
LATENCY = 0.5
HEALTHY_WINDOW = 10
STEADY_WAIT = 120
QUIET_AFTER = 60
DEADLINE = 240
COOLDOWN = 20
POLL = 2
JOBS = 3
JOBS_WAIT = 60
PER_MINUTE = 1000.0
ORDERS = "/orders/{order_id}"


def flat(text: str) -> str:
    return " ".join(str(text).split())


def files(project_root: Path) -> dict[str, Path]:
    obs = project_root / OBS
    return {SLO_FILE: project_root / SLO_FILE, RUNBOOK_YAML: project_root / RUNBOOK_YAML, RUNBOOK_MD: project_root / RUNBOOK_MD,
            SLO_RULES: obs / SLO_RULES, SLO_TESTS: obs / SLO_TESTS}


def require(project_root: Path, *names: str) -> None:
    paths = files(project_root)
    found = [missing(paths[name], DOC) for name in names if not paths[name].is_file()]
    if found:
        pytest.fail("\n".join(found), pytrace=False)


def read_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}", pytrace=False)


def seconds(value) -> float | None:
    if value is None:
        return 0.0
    text = str(value).strip()
    parts = DURATION.findall(text)
    if not parts or "".join(n + u for n, u in parts) != text:
        return None
    return sum(int(n) * UNITS[u] for n, u in parts)


def slo_problems(data) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("slos"), list):
        return [f"{SLO_FILE} cần khoá slos là danh sách"]
    found = []
    if not isinstance(data.get("service"), str) or not data["service"].strip():
        found.append(f"{SLO_FILE}: service là tên dịch vụ (chuỗi)")
    slos = data["slos"]
    names = [s.get("name") for s in slos if isinstance(s, dict)]
    if len(names) != len(slos) or len(set(map(str, names))) != len(names):
        found.append(f"{SLO_FILE}: mỗi SLO là một mapping có name, không trùng")
    slo = next((s for s in slos if isinstance(s, dict) and s.get("name") == SLO_NAME), None)
    if slo is None:
        return found + [f"{SLO_FILE}: thiếu SLO name: {SLO_NAME}"]
    objective = slo.get("objective")
    if isinstance(objective, bool) or not isinstance(objective, (int, float)) or not OBJECTIVE_MIN <= objective <= OBJECTIVE_MAX:
        found.append(f"{SLO_NAME}: objective là số phần trăm từ {OBJECTIVE_MIN} tới {OBJECTIVE_MAX}, đang {objective!r}")
        objective = None
    if slo.get("window") != "30d":
        found.append(f"{SLO_NAME}: window: 30d")
    minutes = slo.get("error_budget_minutes")
    if objective is not None:
        expected = (1 - objective / 100) * 30 * 24 * 60
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or abs(minutes - expected) > 0.5:
            found.append(f"{SLO_NAME}: error_budget_minutes là số phút được phép hỏng trong 30 ngày với objective {objective} "
                         f"(sai số 0,5 phút), đang {minutes!r}")
    for key, size in (("sli", 40), ("rationale", 120)):
        if not isinstance(slo.get(key), str) or len(flat(slo[key])) < size or "TODO" in slo[key]:
            found.append(f"{SLO_NAME}: {key} là đoạn văn ít nhất {size} ký tự")
    return found


def load_slo(project_root: Path) -> dict:
    require(project_root, SLO_FILE)
    data = read_yaml(project_root / SLO_FILE)
    found = slo_problems(data)
    if found:
        pytest.fail("\n".join(found), pytrace=False)
    return next(s for s in data["slos"] if s.get("name") == SLO_NAME)


def rule_slots(data) -> list[tuple[int, int, dict]]:
    groups = data.get("groups") if isinstance(data, dict) else None
    return [(gi, ri, rule) for gi, group in enumerate(groups if isinstance(groups, list) else []) if isinstance(group, dict)
            for ri, rule in enumerate(group.get("rules") if isinstance(group.get("rules"), list) else []) if isinstance(rule, dict)]


def mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def tier_of(rule: dict) -> tuple[str, str]:
    labels = mapping(rule.get("labels"))
    return str(labels.get("severity")), str(labels.get("long_window"))


def unfenced(doc: str) -> str:
    """Dòng bắt đầu bằng '#' trong khối code (```, ~~~) được lùi một khoảng trắng để không thành tiêu đề."""
    out, fence = [], None
    for line in doc.splitlines():
        mark = re.match(r"\s*(```|~~~)", line)
        if mark and fence is None:
            fence = mark.group(1)
        elif mark and line.strip().startswith(fence):
            fence = None
        elif fence is not None and line.startswith("#"):
            line = " " + line
        out.append(line)
    return "\n".join(out)


def runbook_sections(doc: str) -> dict[str, str]:
    parts = re.split(r"^## +(.+?)\s*$", unfenced(doc), flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def subsection(body: str, name: str) -> str:
    match = re.search(rf"^### +{re.escape(name)}\s*$(.*?)(?=^#{{1,3}} |\Z)", unfenced(body), re.M | re.S)
    return match.group(1) if match else ""


def rule_problems(data, sections: dict[str, str]) -> list[str]:
    slots = rule_slots(data)
    if not slots:
        return [f"{SLO_RULES} phải có groups: [ {{name, rules: [...]}} ] với ít nhất một rule"]
    records = {r.get("record") for _, _, r in slots if "record" in r}
    found = [f"Thiếu recording rule {name}" for name in RECORDS if name not in records]
    burns = [r for _, _, r in slots if r.get("alert") == BURN]
    tiers = sorted(tier_of(r) for r in burns)
    if tiers != sorted(TIERS):
        found.append(f"{BURN}: đúng ba rule với nhãn (severity, long_window) {list(TIERS)}, đang {tiers}")
    for rule in burns:
        where = f"{BURN} {'/'.join(tier_of(rule))}"
        wait = seconds(rule.get("for"))
        if wait is None or wait > MAX_FOR:
            found.append(f"{where}: for bỏ trống hoặc không quá 2m, đang {rule.get('for')!r}")
        if "keep_firing_for" in rule:
            found.append(f"{where}: không dùng keep_firing_for (cửa sổ ngắn lo việc tắt alert khi đã hết lỗi)")
        annotations = mapping(rule.get("annotations"))
        if not str(annotations.get("summary", "")).strip():
            found.append(f"{where}: cần annotations.summary")
        match = ANCHOR.search(str(annotations.get("runbook_url", "")).strip())
        if not match:
            found.append(f"{where}: annotations.runbook_url trỏ tới mục của {RUNBOOK_MD}, dạng .../RUNBOOK.md#<mục>")
        elif match.group(1) not in sections:
            found.append(f"{where}: runbook_url trỏ tới #{match.group(1)} nhưng {RUNBOOK_MD} không có '## {match.group(1)}'")
    return found


def sections_of(project_root: Path) -> dict[str, str]:
    path = project_root / RUNBOOK_MD
    return runbook_sections(path.read_text(encoding="utf-8")) if path.is_file() else {}


def runbook_url_anchors(data) -> set[str]:
    found = set()
    for _, _, rule in rule_slots(data):
        if rule.get("alert") == BURN:
            match = ANCHOR.search(str(mapping(rule.get("annotations")).get("runbook_url", "")).strip())
            if match:
                found.add(match.group(1))
    return found


def stripped(data, dest: Path) -> Path:
    """Bản chép tệp rule: alert burn-rate chỉ giữ nhãn severity, long_window và bỏ annotation (promtool so từng chữ)."""
    data = yaml.safe_load(yaml.safe_dump(data))
    for _, _, rule in rule_slots(data):
        if rule.get("alert") == BURN:
            rule.pop("annotations", None)
            labels = mapping(rule.get("labels"))
            rule["labels"] = {k: v for k, v in labels.items() if k in ("severity", "long_window")}
    (dest / "rules").mkdir(parents=True, exist_ok=True)
    (dest / "rules" / "slo.yml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return dest


def series(path: str, status: str, job: str = "olist-api") -> str:
    return f'http_requests_total{{job="{job}", method="GET", path="{path}", status="{status}"}}'


def cumulative(per_minute: list[float]) -> str:
    total, values = 0.0, ["0"]
    for value in per_minute:
        total += value
        values.append(format(total, ".12g"))
    return " ".join(values)


def scenario(segments: list[tuple[int, float]], evals: list[tuple[int, tuple]], extra: list[tuple[str, float]] = (),
             exprs: list[dict] = ()) -> dict:
    """Một nhóm test promtool, mẫu mỗi phút: route tra đơn có PER_MINUTE request/phút, phần `ratio` trả 500 theo từng đoạn
    (số phút, ratio), không có series 500 nào khi mọi ratio bằng 0; `extra` là series khác (tên, request/phút) chạy suốt kịch bản."""
    ratios = [ratio for minutes, ratio in segments for _ in range(minutes)]
    inputs = [{"series": series(ORDERS, "200"), "values": cumulative([PER_MINUTE * (1 - r) for r in ratios])}] if ratios else []
    if any(ratios):
        inputs.append({"series": series(ORDERS, "500"), "values": cumulative([PER_MINUTE * r for r in ratios])})
    length = len(ratios) or max(m for m, _ in evals) + 5
    inputs += [{"series": name, "values": cumulative([rate] * length)} for name, rate in extra]
    if not inputs:
        inputs = [{"series": 'up{job="olist-api"}', "values": f"1x{length}"}]
    return {"interval": "1m", "input_series": inputs,
            "alert_rule_test": [{"eval_time": f"{minute}m", "alertname": BURN,
                                 "exp_alerts": [{"exp_labels": {"severity": s, "long_window": w}} for s, w in tiers]}
                                for minute, tiers in evals],
            "promql_expr_test": list(exprs)}


def scenarios(budget: float) -> dict[str, dict]:
    """Kịch bản ẩn, sinh theo budget = 1 - objective/100 của bạn. Ngưỡng của từng mức: 14,4, 6 và 3 lần budget."""
    fast, slow, low = 20 * budget, 4 * budget, 0.5 * budget
    probes = [(series(p, "200"), PER_MINUTE) for p in ("/metrics", "/healthz", "/readyz")]
    noise = [(series("/readyz", "503"), PER_MINUTE), (series(ORDERS, "500", "olist-api-canary"), PER_MINUTE),
             (series(ORDERS, "200", "olist-api-canary"), PER_MINUTE), (series(ORDERS, "404"), 300.0)]
    zero = [{"expr": name, "eval_time": "65m", "exp_samples": [{"labels": name, "value": 0}]} for name in RECORDS]
    return {
        "70 phút lỗi 20 lần budget từ đầu, có traffic /metrics, /healthz, /readyz không tính vào SLI: cả ba mức bắn ở phút 65; "
        "40 phút sau khi hết lỗi chỉ còn ticket 1d":
            scenario([(70, fast), (45, 0.0)], [(65, TIERS), (110, (("ticket", "1d"),))], probes),
        "6 giờ khoẻ rồi 5 phút lỗi 20 lần budget: không bắn":
            scenario([(400, 0.0), (5, fast)], [(404, ()), (405, ())]),
        "25 giờ lỗi 4 lần budget: chỉ ticket 1d; 140 phút sau khi hết lỗi không còn gì":
            scenario([(1500, slow), (150, 0.0)], [(1500, (("ticket", "1d"),)), (1640, ())]),
        "6 giờ khoẻ, 60 phút lỗi 20 lần budget, rồi hết lỗi: chưa bắn ở phút 10, page 1h ở phút 55, tắt 12 phút sau khi hết lỗi":
            scenario([(400, 0.0), (60, fast), (15, 0.0)], [(410, ()), (455, (("page", "1h"),)), (472, ())]),
        "7 giờ lỗi 10 lần budget: chỉ page 6h và ticket 1d":
            scenario([(430, 10 * budget)], [(420, (("page", "6h"), ("ticket", "1d")))]),
        "25 giờ lỗi nửa budget: không bắn":
            scenario([(1500, low)], [(1500, ())]),
        "lỗi chỉ ở /readyz, ở job olist-api-canary và 4xx: không bắn, mọi recording rule bằng 0":
            scenario([(70, 0.0)], [(65, ())], noise, zero),
        "không có traffic: không bắn":
            scenario([], [(65, ())]),
    }


def coverage_problems(data) -> list[str]:
    tests = data.get("tests") if isinstance(data, dict) else None
    firing, quiet = set(), False
    for test in tests if isinstance(tests, list) else []:
        cases = mapping(test).get("alert_rule_test")
        for case in cases if isinstance(cases, list) else []:
            if not isinstance(case, dict) or case.get("alertname") != BURN:
                continue
            alerts = case.get("exp_alerts") or []
            if not alerts:
                quiet = True
            for alert in alerts if isinstance(alerts, list) else []:
                labels = mapping(mapping(alert).get("exp_labels"))
                firing.add((str(labels.get("severity")), str(labels.get("long_window"))))
    found = [f"{SLO_TESTS}: cần một ca {BURN} bắn mức severity={s}, long_window={w}" for s, w in TIERS if (s, w) not in firing]
    if not quiet:
        found.append(f"{SLO_TESTS}: cần ít nhất một ca {BURN} không bắn (exp_alerts: [])")
    return found


def runbook_problems(data) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return [f"{RUNBOOK_YAML} phải có khoá entries là danh sách"]
    entries = data["entries"]
    found = [] if ENTRIES_MIN <= len(entries) <= ENTRIES_MAX else [
        f"{RUNBOOK_YAML} cần {ENTRIES_MIN} tới {ENTRIES_MAX} entry, có {len(entries)}"]
    seen = set()
    for index, entry in enumerate(entries, 1):
        where = f"entry {index}"
        if not isinstance(entry, dict) or set(entry) != {"id", "detect", "action"}:
            found.append(f"{where}: cần đúng ba khoá id, detect, action")
            continue
        if not isinstance(entry["id"], str) or not ID.fullmatch(entry["id"]) or entry["id"] in seen:
            found.append(f"{where}: id {entry['id']!r} phải là chữ thường, số, '-', không trùng")
        seen.add(str(entry["id"]))
        detect = entry["detect"]
        if not isinstance(detect, dict) or len(detect) != 1 or not set(detect) <= {"promql", "logql"}:
            found.append(f"{where}: detect cần đúng một khoá promql hoặc logql")
        else:
            (kind, query), = detect.items()
            if not isinstance(query, str) or not query.strip() or "TODO" in query:
                found.append(f"{where}: detect.{kind} còn trống")
            elif kind == "logql" and not query.strip().startswith("{"):
                found.append(f"{where}: detect.logql phải là log query bắt đầu bằng {{...}}")
        action = entry["action"]
        if not isinstance(action, dict) or set(action) != {"do", "service"}:
            found.append(f"{where}: action cần đúng hai khoá do, service")
        elif action["do"] not in ACTIONS or action["service"] not in SERVICES:
            found.append(f"{where}: action.do thuộc {ACTIONS}, action.service thuộc {SERVICES}")
    return found


def load_runbook(project_root: Path) -> list[dict]:
    require(project_root, RUNBOOK_YAML)
    data = read_yaml(project_root / RUNBOOK_YAML)
    found = runbook_problems(data)
    if found:
        pytest.fail("\n".join(found), pytrace=False)
    return data["entries"]


def section_problems(name: str, body: str) -> list[str]:
    return [f"{name}: phần '### {s}' thiếu hoặc quá ngắn (ít nhất 40 ký tự)" for s in SECTIONS if len(flat(subsection(body, s))) < 40]


def runbook_md_problems(doc: str, entries: list[dict], anchors: set[str]) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    sections = runbook_sections(doc)
    for entry in entries:
        body = sections.get(entry["id"])
        if body is None:
            found.append(f"Thiếu phần '## {entry['id']}'")
            continue
        found += section_problems(entry["id"], body)
        query = next(iter(entry["detect"].values()))
        if flat(query) not in flat(subsection(body, "Chẩn đoán")):
            found.append(f"{entry['id']}: phần Chẩn đoán phải chép nguyên truy vấn detect của entry")
        recover = flat(subsection(body, "Khôi phục"))
        if f"{entry['action']['do']} {entry['action']['service']}" not in recover:
            found.append(f"{entry['id']}: phần Khôi phục phải nêu hành động '{entry['action']['do']} {entry['action']['service']}'")
    for anchor in sorted(anchors - {e["id"] for e in entries}):
        if anchor in sections:
            found += section_problems(anchor, sections[anchor])
    return found


def detect_rules(entries: list[dict]) -> dict:
    rules = [{"record": f"m09:detect_{i}", "expr": entry["detect"]["promql"]}
             for i, entry in enumerate(entries) if "promql" in entry["detect"]]
    return {"groups": [{"name": "runbook-detect", "rules": rules}]}


def routed(config_dir: Path, labels: dict) -> str:
    result = amtool("config", "routes", "test", f"--config.file={Path(ALERTMANAGER).name}",
                    *[f"{k}={v}" for k, v in sorted(labels.items())], cwd=config_dir)
    return result.stdout.strip() if result.returncode == 0 else f"lỗi: {(result.stderr or result.stdout).strip()[-300:]}"


def test_m09_slo_file(project_root):
    load_slo(project_root)


def test_m09_slo_rules_valid(project_root):
    require(project_root, SLO_RULES, RUNBOOK_MD)
    obs = project_root / OBS
    result = promtool("check", "rules", SLO_RULES, cwd=obs)
    assert result.returncode == 0, f"promtool check rules {SLO_RULES}:\n{(result.stdout + result.stderr)[-1500:]}"
    found = rule_problems(read_yaml(obs / SLO_RULES), sections_of(project_root))
    assert not found, "\n".join(found)


@pytest.mark.parametrize("index", range(len(scenarios(0.005))), ids=[f"kịch-bản-{i + 1}" for i in range(len(scenarios(0.005)))])
def test_m09_burn_rate_matches_objective(project_root, tmp_path, index):
    slo = load_slo(project_root)
    require(project_root, SLO_RULES)
    data = read_yaml(project_root / OBS / SLO_RULES)
    if not rule_slots(data):
        pytest.fail(f"{SLO_RULES} phải có groups: [ {{name, rules: [...]}} ] với ít nhất một rule", pytrace=False)
    budget = 1 - slo["objective"] / 100
    name, test = list(scenarios(budget).items())[index]
    work = stripped(data, tmp_path / "hidden")
    (work / "hidden.test.yml").write_text(yaml.safe_dump({"rule_files": ["rules/slo.yml"], "evaluation_interval": "1m",
                                                         "tests": [test]}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    result = promtool("test", "rules", "hidden.test.yml", cwd=work)
    assert result.returncode == 0, (
        f"Kịch bản '{name}' (objective {slo['objective']}, budget {budget:.4%}) không ra đúng alert hay giá trị:\n"
        f"{(result.stdout + result.stderr)[-2500:]}")


def test_m09_slo_rule_tests_pass_and_cover(project_root):
    require(project_root, SLO_RULES, SLO_TESTS)
    folder = project_root / OBS / "prometheus"
    result = promtool("test", "rules", Path(SLO_TESTS).name, cwd=folder)
    assert result.returncode == 0, f"promtool test rules {SLO_TESTS}:\n{(result.stdout + result.stderr)[-2000:]}"
    found = coverage_problems(read_yaml(project_root / OBS / SLO_TESTS))
    assert not found, "\n".join(found)


def test_m09_burn_alerts_routed(project_root):
    require(project_root, SLO_RULES)
    config = project_root / OBS / ALERTMANAGER
    if not config.is_file():
        pytest.fail(missing(config, "m08-observability.md") + " (M09 dùng route của M08)", pytrace=False)
    burns = [r for _, _, r in rule_slots(read_yaml(project_root / OBS / SLO_RULES)) if r.get("alert") == BURN]
    assert burns, f"{SLO_RULES} chưa có alert {BURN}"
    found = []
    for rule in burns:
        labels = {k: str(v) for k, v in mapping(rule.get("labels")).items()} | {"alertname": BURN}
        want = ROUTES.get(labels.get("severity", ""))
        got = routed(config.parent, labels)
        if got != want:
            found.append(f"{BURN} {labels} phải tới đúng receiver {want}, đang tới {got!r}")
    assert not found, "\n".join(found)


def test_m09_runbook_yaml(project_root, tmp_path):
    entries = load_runbook(project_root)
    rules = detect_rules(entries)
    if rules["groups"][0]["rules"]:
        (tmp_path / "detect.yml").write_text(yaml.safe_dump(rules, sort_keys=False, allow_unicode=True), encoding="utf-8")
        result = promtool("check", "rules", "detect.yml", cwd=tmp_path)
        assert result.returncode == 0, f"detect.promql của runbook không phải PromQL hợp lệ:\n{(result.stdout + result.stderr)[-1500:]}"


def test_m09_runbook_md(project_root):
    entries = load_runbook(project_root)
    require(project_root, RUNBOOK_MD)
    rules = project_root / OBS / SLO_RULES
    anchors = runbook_url_anchors(read_yaml(rules)) if rules.is_file() else set()
    found = runbook_md_problems((project_root / RUNBOOK_MD).read_text(encoding="utf-8"), entries, anchors)
    assert not found, "\n".join(found)


class Probes(threading.Thread):
    """Khách giả: tra đơn, gọi /readyz, đẩy job; ghi (thời điểm, loại, đạt) cho từng request."""

    def __init__(self, base: str) -> None:
        super().__init__(daemon=True)
        self.base = base
        self.samples: list[tuple[float, str, bool]] = []
        self.stopping = threading.Event()

    def probe(self, client: httpx.Client, kind: str, method: str, path: str, ok_status: tuple[int, ...]) -> None:
        start = time.monotonic()
        try:
            response = client.request(method, self.base + path)
            ok = response.status_code in ok_status and time.monotonic() - start < LATENCY
        except httpx.HTTPError:
            ok = False
        self.samples.append((time.monotonic(), kind, ok))

    def run(self) -> None:
        with httpx.Client(trust_env=False, timeout=3) as client:
            turn = 0
            while not self.stopping.is_set():
                self.probe(client, "orders", "GET", f"/orders/m09-{turn % 50:03d}", (200, 404))
                self.probe(client, "readyz", "GET", "/readyz", (200,))
                if turn % 4 == 0:
                    self.probe(client, "jobs", "POST", "/jobs/recompute", (202,))
                turn += 1
                self.stopping.wait(0.2)

    def since(self, start: float) -> list[tuple[float, str, bool]]:
        return [s for s in list(self.samples) if s[0] >= start]

    def healthy(self, since: float) -> bool:
        now = time.monotonic()
        if now - since < HEALTHY_WINDOW:
            return False
        recent = self.since(now - HEALTHY_WINDOW)
        kinds = {kind: [ok for _, k, ok in recent if k == kind] for kind in ("orders", "readyz", "jobs")}
        return len(kinds["orders"]) >= 8 and len(kinds["readyz"]) >= 5 and len(kinds["jobs"]) >= 1 and all(
            all(values) for values in kinds.values())

    def wait_healthy(self, since: float, timeout: float) -> float | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.healthy(since):
                return time.monotonic()
            time.sleep(1)
        return None


class Observed:
    def __init__(self) -> None:
        self.error = ""
        self.failure = ""
        self.seed: int | None = None
        self.steps: dict[str, dict] = {}

    def step(self, name: str) -> dict:
        if self.error:
            pytest.fail(self.error, pytrace=False)
        if name not in self.steps:
            pytest.fail(f"Chưa tới bước {name}: {self.failure or 'bước trước lỗi'}", pytrace=False)
        return self.steps[name]


def run_seed() -> int:
    value = os.environ.get(SEED_ENV, "").strip()
    if value:
        if not value.isdigit():
            pytest.fail(f"{SEED_ENV} phải là số nguyên không âm, đang {value!r}", pytrace=False)
        return int(value)
    return time.time_ns() // 1000 % 1_000_000


def rerun(seed: int) -> str:
    return (f"Chạy lại đúng sự cố này: {SEED_ENV}={seed} uv run pytest tracks/devops/capstone/project/tests -q -rs -s -k m09")


def matched(stack: ObsStack, entry: dict, since: float) -> bool:
    (kind, query), = entry["detect"].items()
    try:
        if kind == "promql":
            return bool(stack.prom_query(query))
        return bool(stack.loki_query(query, since=max(since, 5), limit=1))
    except pytest.fail.Exception as error:
        raise AssertionError(f"Entry '{entry['id']}': truy vấn detect lỗi khi chạy: {str(error)[:500]}") from None


def act(project, action: dict) -> None:
    service = action["service"]
    if action["do"] == "recreate":
        result = project.run("up", "-d", "--no-deps", "--force-recreate", "--no-build", "--pull", "never", service, timeout=180)
    else:
        result = project.run(action["do"], service, timeout=180)
    if result.returncode != 0:
        raise AssertionError(f"docker compose {action['do']} {service} lỗi: {result.stderr.strip()[-1500:]}")


def stage(dest: Path, root: Path, project_root: Path) -> Path:
    dest.mkdir(parents=True)
    shutil.copyfile(root / COMPOSE, dest / "compose.yaml")
    shutil.copytree(project_root / OBS, dest / OBS, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def rules_step(stack: ObsStack) -> dict:
    with httpx.Client(trust_env=False, timeout=10) as client:
        groups = client.get(stack.url("prometheus") + "/api/v1/rules").json()["data"]["groups"]
    rules = [{"name": r.get("name"), "health": r.get("health"), "error": r.get("lastError", "")}
             for g in groups for r in g.get("rules") or []]
    ratio = stack.prom_query(RECORDS[0], timeout=60)
    burning = stack.prom_query(f'ALERTS{{alertname="{BURN}"}}')
    return {"rules": rules, "ratio": ratio, "burning": burning}


def processed(stack: ObsStack) -> float | None:
    result = stack.prom_query('sum(jobs_processed_total{job="olist-worker"})')
    return float(result[0]["value"][1]) if result else None


def game_day(stack: ObsStack, lab: DockerLab, probes: Probes, entries: list[dict], seed: int) -> dict:
    with warnings.catch_warnings(record=True) as caught, \
            FaultInjector(lab, seed=seed, faults=list(FAULTS), services=list(FAULT_SERVICES), delay_ms=DELAY_MS) as injector:
        warnings.simplefilter("always")
        try:
            code = injector.inject()
        except (pytest.fail.Exception, RuntimeError, OSError, subprocess.TimeoutExpired, KeyError, ValueError):
            raise AssertionError(f"Seed {seed}: không bơm được lỗi (lỗi môi trường, không phải runbook; chi tiết ẩn để không lộ "
                                 f"lỗi). {rerun(seed)}") from None
        injected = mark = time.monotonic()
        actions: list[dict] = []
        recovered = None
        while time.monotonic() - injected < DEADLINE:
            time.sleep(POLL)
            now = time.monotonic()
            if probes.healthy(mark):
                recovered = now
                break
            still_failing = any(not ok for _, _, ok in probes.since(now - COOLDOWN / 2))
            if actions and (now - mark < COOLDOWN or not still_failing):
                continue
            done = {a["id"] for a in actions}
            hit = next((e for e in entries if e["id"] not in done and matched(stack, e, now - mark)), None)
            if hit is not None:
                act(stack.project, hit["action"])
                actions.append({"id": hit["id"], "action": f"{hit['action']['do']} {hit['action']['service']}",
                                "at": now - injected})
                mark = time.monotonic()
        samples = probes.since(injected)
        result = {"code": code, "resource": injector.resource, "actions": actions,
                  "recovered": None if recovered is None else recovered - injected,
                  "failed": sum(1 for _, _, ok in samples if not ok), "total": len(samples)}
    result["warnings"] = [str(w.message) for w in caught]
    if recovered is not None:
        start = processed(stack)
        deadline = time.monotonic() + JOBS_WAIT
        latest = start
        while time.monotonic() < deadline and (start is None or latest is None or latest < start + JOBS):
            time.sleep(3)
            latest = processed(stack)
            start = latest if start is None else start
        result["jobs"] = {"start": start, "latest": latest}
    return result


@pytest.fixture(scope="module")
def observed(project_root, tmp_path_factory):
    state = Observed()
    needed = [(project_root / COMPOSE, "m03-containers.md"), (project_root / DOCKERFILE, "m03-containers.md"),
              (project_root / OBS / ALERTMANAGER, "m08-observability.md"), *((p, DOC) for p in files(project_root).values())]
    found = [missing(path, doc) for path, doc in needed if not path.is_file()]
    if not found:
        data = read_yaml(project_root / RUNBOOK_YAML)
        found = runbook_problems(data)
    if found:
        state.error = "Không dựng game day: " + "\n".join(found)
        yield state
        return
    entries = data["entries"]
    Exercise.require_tool("docker")
    Exercise.require_image(FAULT_NETEM_IMAGE, f"Build image tc của FaultInjector bằng: {FAULT_NETEM_BUILD}")
    tmp = tmp_path_factory.mktemp("m09")
    root = assemble(tmp / "repo", project_root)
    state.seed = run_seed()
    with DockerLab() as lab:
        probes = None
        try:
            tags = build_targets(lab, root, {"APP_VERSION": f"m09-{uuid.uuid4().hex[:8]}",
                                             "GIT_COMMIT": uuid.uuid4().hex + uuid.uuid4().hex[:8]})
            env = {"OLIST_API_IMAGE": tags["api"], "OLIST_WORKER_IMAGE": tags["worker"], "POSTGRES_PASSWORD": secrets.token_hex(12),
                   "OTEL_EXPORTER_OTLP_ENDPOINT": COLLECTOR}
            stack = ObsStack(lab, project=stage(tmp / "stage", root, project_root), env=env)
            print(f"\nM09: stack của game day đã chạy. Grafana {stack.url('grafana')} (dashboard Olist Shop), Prometheus "
                  f"{stack.url('prometheus')}, Alertmanager {stack.url('alertmanager')}", flush=True)
            probes = Probes(f"http://127.0.0.1:{stack.project.port('api', 8000)}")
            started = time.monotonic()
            probes.start()
            steady = probes.wait_healthy(started, STEADY_WAIT)
            if steady is None:
                raise AssertionError(f"Olist Shop chưa khoẻ {HEALTHY_WINDOW} giây liền trong {STEADY_WAIT} giây đầu (trước khi bơm lỗi):\n"
                                     f"{stack.project.logs(tail=20)[-2000:]}")
            time.sleep(QUIET_AFTER)
            state.steps["rules"] = rules_step(stack)
            noisy = [e["id"] for e in entries if matched(stack, e, time.monotonic() - steady)]
            state.steps["quiet"] = {"noisy": noisy}
            if noisy:
                raise AssertionError("bỏ qua game day vì runbook báo động giả khi hệ thống đang khoẻ")
            state.steps["game"] = game_day(stack, lab, probes, entries, state.seed)
        except (pytest.fail.Exception, AssertionError, httpx.HTTPError, KeyError, ValueError, subprocess.TimeoutExpired,
                RuntimeError, OSError) as error:
            state.failure = f"{type(error).__name__}: {error}"
        finally:
            if probes is not None:
                probes.stopping.set()
                probes.join(10)
        yield state


def test_m09_live_slo_rules_loaded(observed):
    step = observed.step("rules")
    names = {r["name"] for r in step["rules"]}
    absent = [name for name in (*RECORDS, BURN) if name not in names]
    assert not absent, f"Prometheus của stack chưa nạp {absent} (tệp phải ở observability/{SLO_RULES})"
    unhealthy = [f"{r['name']}: {r['error']}" for r in step["rules"] if r["health"] != "ok"]
    assert not unhealthy, f"Rule lỗi khi chạy trên Prometheus thật: {unhealthy}"
    shapes = [r.get("metric", {}) for r in step["ratio"]]
    assert shapes == [{"__name__": RECORDS[0]}], (
        f"{RECORDS[0]} phải ra đúng một series chỉ có __name__ khi có traffic thật (metric của stack M08): {shapes}")
    assert not step["burning"], f"{BURN} đã pending hay firing khi hệ thống đang khoẻ: {step['burning']}"


def test_m09_live_runbook_quiet(observed):
    noisy = observed.step("quiet")["noisy"]
    assert not noisy, f"Entry {', '.join(noisy)} khớp khi hệ thống đang khoẻ: detect phải im lặng ở trạng thái bình thường"


def test_m09_live_game_day_recovers(observed):
    step = observed.step("game")
    seed = observed.seed
    assert step["failed"], (f"Seed {seed}: không request nào hỏng sau khi bơm lỗi (lỗi môi trường, không phải runbook). "
                            f"{rerun(seed)}")
    assert step["actions"], f"Seed {seed}: không entry nào của runbook.yaml khớp trong {DEADLINE} giây sau khi bơm lỗi. {rerun(seed)}"
    done = ", ".join(f"'{a['id']}' ({a['action']}) ở giây {a['at']:.0f}" for a in step["actions"])
    assert step["recovered"] is not None, (
        f"Seed {seed}: hệ thống chưa khoẻ {HEALTHY_WINDOW} giây liền trong {DEADLINE} giây sau khi bơm lỗi; entry đã chạy: {done}. "
        f"{rerun(seed)}")
    jobs = step.get("jobs") or {}
    assert jobs.get("start") is not None and jobs.get("latest") is not None and jobs["latest"] >= jobs["start"] + JOBS, (
        f"Seed {seed}: sau khi khôi phục, worker không xử lý thêm {JOBS} job trong {JOBS_WAIT} giây "
        f"(jobs_processed_total: {jobs}). {rerun(seed)}")
    print(f"\nGame day M09, seed {seed}: lỗi {step['code']} vào {step['resource']}. Entry đã chạy: {done}. Khoẻ lại "
          f"{HEALTHY_WINDOW} giây liền ở giây {step['recovered']:.0f} sau khi bơm. Request của khách giả hỏng: "
          f"{step['failed']}/{step['total']}.\n{rerun(seed)}")
    for message in step.get("warnings") or []:
        print(f"Cảnh báo khi hoàn tác lỗi: {message}")


def test_m09_checks_catch_bad_files():
    """Bộ kiểm tĩnh bắt được SLO sai budget, rule thiếu mức hay runbook_url sai, runbook thiếu mục, test promtool không phủ."""
    slo = {"service": "olist-shop", "slos": [{"name": SLO_NAME, "objective": 99.9, "window": "30d", "error_budget_minutes": 432,
                                              "sli": "x" * 40, "rationale": "TODO"}]}
    found = "\n".join(slo_problems(slo))
    assert "error_budget_minutes" in found and f"{SLO_NAME}: rationale" in found and f"{SLO_NAME}: sli" not in found, found
    assert slo_problems({"service": "x", "slos": [{"name": SLO_NAME, "objective": "99.9%"}]})
    assert slo_problems({"slos": "x"}) and slo_problems([])
    good = {"name": SLO_NAME, "objective": 99.5, "window": "30d", "error_budget_minutes": 216, "sli": "s" * 40, "rationale": "r" * 120}
    assert slo_problems({"service": "olist-shop", "slos": [good]}) == []
    rules = {"groups": [{"name": "slo", "rules": [
        *[{"record": name, "expr": "vector(0)"} for name in RECORDS[:-1]],
        {"alert": BURN, "expr": "vector(1)", "for": "5m", "labels": {"severity": "page", "long_window": "1h"},
         "annotations": {"summary": "s", "runbook_url": "https://x/RUNBOOK.md#slo-burn"}},
        {"alert": BURN, "expr": "vector(1)", "labels": {"severity": "page", "long_window": "6h"},
         "annotations": {"summary": "s", "runbook_url": "https://x/RUNBOOK.md#khong-co"}},
        {"alert": BURN, "expr": "vector(1)", "keep_firing_for": "5m", "labels": {"severity": "ticket", "long_window": "1d"},
         "annotations": {"summary": "s", "runbook_url": "https://example.invalid/slo"}}]}]}
    found = "\n".join(rule_problems(rules, {"slo-burn": ""}))
    for needle in (f"Thiếu recording rule {RECORDS[-1]}", "page/1h: for", "#khong-co", "ticket/1d: không dùng keep_firing_for",
                   "ticket/1d: annotations.runbook_url"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
    assert "Thiếu recording rule" in "\n".join(rule_problems({"groups": [{"name": "x", "rules": [{"record": "a", "expr": "1"}]}]}, {}))
    assert rule_problems({"groups": "x"}, {}) and seconds("1m30s") == 90 and seconds("2 m") is None
    entries = [{"id": "db-down", "detect": {"promql": "up == 0"}, "action": {"do": "start", "service": "postgres"}}]
    bad = {"entries": [*entries, {"id": "Bad", "detect": {"promql": "x"}, "action": {"do": "start", "service": "api"}},
                       {"id": "two", "detect": {"promql": "x", "logql": "{a}"}, "action": {"do": "start", "service": "api"}},
                       {"id": "act", "detect": {"logql": "x"}, "action": {"do": "kill", "service": "api"}}]}
    found = "\n".join(runbook_problems(bad))
    for needle in ("entry 2: id", "entry 3: detect cần đúng một khoá", "entry 4: detect.logql", "entry 4: action.do"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
    assert runbook_problems({"entries": entries}) and runbook_problems(["x"])
    full = "".join(f"### {s}\n\n{'n' * 50} up == 0 start postgres\n\n" for s in SECTIONS)
    assert runbook_md_problems(f"# R\n\n## db-down\n\n{full}## slo-burn\n\n{full}", entries, {"slo-burn"}) == []
    weak = f"# R\n\n## db-down\n\n### Triệu chứng\n\nngắn\n\n## slo-burn\n\n{full.replace('### Leo thang', '### Khác')}"
    found = "\n".join(runbook_md_problems(weak, entries, {"slo-burn"}))
    for needle in ("db-down: phần '### Tác động'", "Chẩn đoán phải chép nguyên", "Khôi phục phải nêu", "slo-burn: phần '### Leo thang'"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
    tests = {"tests": [{"alert_rule_test": [{"alertname": BURN, "eval_time": "1m",
                                             "exp_alerts": [{"exp_labels": {"severity": "page", "long_window": "1h"}}]}]}]}
    found = "\n".join(coverage_problems(tests))
    assert "long_window=6h" in found and "long_window=1d" in found and "không bắn" in found and "long_window=1h" not in found
    assert len(coverage_problems({"tests": "x"})) == len(TIERS) + 1
    hidden = scenarios(0.005)
    assert len(hidden) == 8 and all(t["alert_rule_test"] for t in hidden.values())
    assert cumulative([1.5, 2.5]) == "0 1.5 4"
    fenced = f"# R\n\n## db-down\n\n```bash\n## khong-phai-muc\n### Leo thang\nkhong-phai-muc\n```\n\n{full}"
    assert set(runbook_sections(fenced)) == {"db-down"} and "khong-phai-muc" not in subsection(fenced, "Leo thang")
