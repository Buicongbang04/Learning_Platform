"""M18: đánh giá độc lập mức senior: design doc nền tảng ETA nhiều market, SLO và burn rate, dẫn xử lý sự cố, postmortem.

Đề ở capstone/milestones/m18-senior-assessment.md. Dữ liệu sự cố dựng bằng `etakit.incident_data` từ ngày thật 2019-11-14.
"""

import math
import re

import pandas as pd
import pytest
import yaml
from etakit import incident_data, incident_facts, require_file

import mlopskit

WINDOW_DAYS = 30
QUALITY_TARGET, FRESHNESS_TARGET = 0.90, 0.99
GOOD_REL, GOOD_ABS_S = 0.3, 300
BUCKET_MIN, MIN_REQUESTS, START_RATIO, CLEAR_RATIO = 5, 20, 0.6, 0.4
STALE_S = 900
SEV1_BUCKETS = 6
SEV2_PCT = 5.0
SLO_NAMES = {"availability", "latency", "quality", "freshness"}
KINDS = {"events", "time"}
DECISIONS = {"rollback", "restart", "scale-out", "wait", "disable-feature", "failover"}
CAUSES = {"stale_feature", "unsafe_default", "skipped_canary", "missing_freshness_alert", "config_change", "model_regression",
          "traffic_spike", "label_delay", "upstream_data_change"}
ROLES = {"incident_commander", "comms", "ops"}
IMPACT_INT = ["affected_requests", "bad_predictions", "stale_minutes"]
IMPACT_PCT = ["quality_budget_consumed_pct", "freshness_budget_consumed_pct"]
TIME = re.compile(r"^\d\d:\d\d$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALERTS = {
    "ETAMarketQualityFastBurn": ("critical", 600),
    "ETAMarketQualitySlowBurn": ("warning", 1800),
    "ETAMarketFeatureStale": ("critical", 300),
    "ETAMarketLabelsMissing": ("warning", 1800),
}
BURN_ALERTS = ["ETAMarketQualityFastBurn", "ETAMarketQualitySlowBurn", "ETAMarketFeatureStale"]
QUALITY = 'eta_quality_checks_total{{job="eta",market="{}",outcome="{}"}}'
REQUESTS = 'eta_requests_total{{job="eta",market="{}"}}'
FRESHNESS = 'eta_feature_last_success_timestamp_seconds{{job="feature-pipeline",market="{}",feature_view="zone_speed_15m"}}'
POSTMORTEM_HEADINGS = ["Tóm tắt", "Tác động", "Dòng thời gian", "Nguyên nhân", "Điều làm tốt", "Hành động"]
ACTION_KINDS = {"ngăn chặn", "phát hiện", "giảm thiệt hại"}
BLAME = ["lỗi của", "cẩu thả", "bất cẩn", "đáng lẽ", "cẩn thận hơn", "chú ý hơn"]
DESIGN_SECTIONS = 11


def words(value) -> int:
    return len(value.split()) if isinstance(value, str) else 0


def minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def load_yaml(*parts: str) -> dict:
    path = require_file(*parts)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path.name} phải là một mapping YAML"
    return data


def heading_texts(text: str) -> list[str]:
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"^#{1,4} ", line):
            out.append(line.lstrip("#").strip())
    return out


def has_heading(found: list[str], name: str) -> bool:
    return any(t.startswith(name) or re.match(rf"^\d+(\.\d+)*\.? {re.escape(name)}", t) for t in found)


def section(text: str, name: str) -> str:
    lines, inside, level, fenced = [], False, 0, False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        match = None if fenced else re.match(r"^(#{1,4}) (.+)$", line)
        if match and inside and len(match.group(1)) <= level:
            break
        if match and not inside and has_heading([match.group(2).strip()], name):
            inside, level = True, len(match.group(1))
            continue
        if inside:
            lines.append(line)
    return "\n".join(lines)


def numbered(text: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def table(text: str) -> tuple[list[str], list[list[str]]]:
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        return [], []
    return [c.lower() for c in rows[0]], rows[2:]


def bullets(text: str) -> list[str]:
    return re.findall(r"^\s*(?:-|\*|\d+\.)\s+(.+)$", text, re.M)


def prose(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.strip() and not line.strip().startswith("|"):
            kept.append(line)
    return "\n".join(kept).strip()


def integer_in(text: str, value: int) -> bool:
    digits = {int(re.sub(r"[ .,_\u202f\u00a0]", "", n)) for n in re.findall(r"\d{1,3}(?:[ .,_\u202f\u00a0]\d{3})+|\d+", text)}
    return value in digits


@pytest.fixture(scope="module")
def incident(tmp_path_factory):
    """Dựng dữ liệu sự cố một lần cho cả module; chạy khi test gọi `incident()` để thiếu tệp nộp thì fail, không ERROR."""
    cache = {}

    def build():
        if "truth" not in cache:
            cache["truth"] = derive(incident_data(tmp_path_factory.mktemp("m18-incident")))
        return cache["truth"]

    return build


def derive(folder) -> dict:
    preds = pd.read_parquet(folder / "predictions.parquet")
    labels = pd.read_parquet(folder / "labels.parquet")
    trips = preds.merge(labels, on="request_id", validate="one_to_one")
    trips["bad"] = (trips["eta_s"] - trips["duration_s"]).abs() > GOOD_REL * trips["duration_s"] + GOOD_ABS_S
    trips["bucket"] = trips["ts"].dt.floor(f"{BUCKET_MIN}min").dt.strftime("%H:%M")
    trips["minute"] = trips["ts"].dt.strftime("%H:%M")
    requests_day = trips.groupby("market").size().to_dict()
    peak_minute = trips.groupby(["market", "minute"]).size().groupby("market").max().to_dict()
    buckets = trips.groupby(["market", "bucket"])["bad"].agg(["mean", "size"]).reset_index()
    buckets = buckets[buckets["size"] >= MIN_REQUESTS]
    hot = buckets[buckets["mean"] > START_RATIO]
    affected = sorted(hot["market"].unique())
    truth = {"requests_day": requests_day, "peak_minute": peak_minute, "affected": affected, "hot_buckets": len(hot)}
    if not affected:
        return truth
    started = hot["bucket"].min()
    mine = buckets[buckets["market"].isin(affected)].sort_values("bucket")
    later_ok = mine.groupby("bucket")["mean"].max()[::-1].le(CLEAR_RATIO).cummin()[::-1]
    mitigated = next(b for b, ok in later_ok.items() if ok and b > started)
    window = trips[trips["market"].isin(affected) & (trips["bucket"] >= started) & (trips["bucket"] < mitigated)]
    fresh = pd.read_csv(folder / "freshness.csv")
    stale = int(((fresh["age_s"] > STALE_S) & fresh["market"].isin(affected)).sum())
    budget_events = (1 - QUALITY_TARGET) * WINDOW_DAYS * sum(requests_day[m] for m in affected)
    budget_minutes = (1 - FRESHNESS_TARGET) * WINDOW_DAYS * 1440 * len(affected)
    impact = {
        "affected_requests": len(window), "bad_predictions": int(window["bad"].sum()), "stale_minutes": stale,
        "quality_budget_consumed_pct": int(window["bad"].sum()) / budget_events * 100,
        "freshness_budget_consumed_pct": stale / budget_minutes * 100,
    }
    pct = max(impact["quality_budget_consumed_pct"], impact["freshness_budget_consumed_pct"])
    severity = "SEV1" if len(hot) >= SEV1_BUCKETS else "SEV2" if pct >= SEV2_PCT else "SEV3"
    truth.update(started_at=started, mitigated_at=mitigated, impact=impact, severity=severity, trips=trips, freshness=fresh)
    return truth


def test_m18_incident_valid(project):
    data = load_yaml("reports", "senior", "incident.yaml")
    facts = incident_facts()
    assert str(data.get("date")) == facts["date"], f"date phải là ngày sự cố \"{facts['date']}\" (trong ngoặc kép)"
    markets = data.get("affected_markets")
    assert isinstance(markets, list) and markets and set(markets) <= set(facts["markets"]), \
        f"affected_markets là danh sách không rỗng, mỗi phần tử thuộc {facts['markets']}"
    for field in ("started_at", "detected_at", "mitigated_at"):
        value = data.get(field)
        assert isinstance(value, str) and TIME.match(value), f"{field}: dạng \"HH:MM\" trong ngoặc kép"
    started, detected, mitigated = (minutes(data[k]) for k in ("started_at", "detected_at", "mitigated_at"))
    assert data.get("time_to_detect_min") == detected - started, "time_to_detect_min = detected_at - started_at (phút)"
    assert data.get("time_to_mitigate_min") == mitigated - started, "time_to_mitigate_min = mitigated_at - started_at (phút)"
    assert data.get("severity") in {"SEV1", "SEV2", "SEV3"}, "severity thuộc SEV1 | SEV2 | SEV3"
    assert data.get("decision") in DECISIONS, f"decision thuộc {sorted(DECISIONS)}"
    assert isinstance(data.get("trigger"), str) and data["trigger"].strip(), "trigger là một deploy_id"
    causes = data.get("causes")
    assert isinstance(causes, list) and causes, "causes là danh sách nhãn không rỗng"
    unknown = [c for c in causes if c not in CAUSES]
    assert not unknown, f"causes có nhãn ngoài bảng mục 4: {unknown}"
    assert len(set(causes)) == len(causes), "causes không lặp nhãn"
    impact = data.get("impact")
    assert isinstance(impact, dict), "impact là mapping"
    for key in IMPACT_INT:
        assert isinstance(impact.get(key), int) and not isinstance(impact.get(key), bool), f"impact.{key} là số nguyên"
    for key in IMPACT_PCT:
        value = impact.get(key)
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"impact.{key} là số"
    roles = data.get("roles") or {}
    assert set(roles) == ROLES, f"roles cần đúng các khoá {sorted(ROLES)}"
    assert len({str(v).lstrip("@") for v in roles.values()}) == 3, "ba vai trò do ba người khác nhau giữ"
    reasons = data.get("reasons") or []
    assert len(reasons) >= 2 and all(words(r) >= 6 and re.search(r"\d", r) for r in reasons), \
        "cần ≥2 reasons, mỗi lý do là một câu ≥6 từ có số liệu"


def test_m18_incident_causes(project):
    data = load_yaml("reports", "senior", "incident.yaml")
    claimed = {c for c in data.get("causes") or [] if isinstance(c, str)}
    truth = incident_facts()["causes"]
    missed, extra = len(truth - claimed), len(claimed - truth)
    assert missed == 0, f"còn {missed} nguyên nhân hoặc yếu tố góp phần chưa có trong causes"
    assert extra == 0, f"có {extra} nhãn trong causes không đúng với sự cố này"


def test_m18_incident_matches_data(project, incident):
    data = load_yaml("reports", "senior", "incident.yaml")
    facts = incident_facts()
    truth = incident()
    assert truth["affected"], "Dữ liệu sự cố không có khung tệp nào: tệp nguồn đổi, tải lại nyc-tlc"
    wrong = len(set(data.get("affected_markets") or []) ^ set(truth["affected"]))
    assert wrong == 0, f"affected_markets lệch {wrong} market so với định nghĩa ở mục 4"
    for field in ("started_at", "mitigated_at"):
        same = data.get(field) == truth[field]
        assert same, f"{field} chưa khớp định nghĩa ở mục 4"
    checks = {
        "detected_at": "detected_at chưa khớp alerts.log và chat.log theo định nghĩa",
        "trigger": "trigger chưa phải thay đổi đưa thành phần hỏng vào đường phục vụ",
        "decision": "decision chưa phải hành động đã chấm dứt tác động",
    }
    for field, message in checks.items():
        same = data.get(field) == facts[field]
        assert same, message
    same = data.get("severity") == truth["severity"]
    assert same, "severity chưa khớp bảng phân loại"
    roles = {k: str(v).lstrip("@") for k, v in (data.get("roles") or {}).items()}
    wrong_roles = sum(roles.get(k) != v for k, v in facts["roles"].items())
    assert wrong_roles == 0, f"{wrong_roles} vai trò chưa khớp kênh sự cố"
    impact = data.get("impact") or {}
    for key in IMPACT_INT:
        same = impact.get(key) == truth["impact"][key]
        assert same, f"impact.{key} = {impact.get(key)} chưa khớp số tính lại (bằng đúng)"
    for key in IMPACT_PCT:
        value = impact.get(key)
        ok = isinstance(value, (int, float)) and abs(value - truth["impact"][key]) <= 0.05
        assert ok, f"impact.{key} = {value} chưa khớp số tính lại (sai số 0.05 điểm phần trăm)"


def test_m18_slo_valid(project):
    data = load_yaml("reports", "senior", "slo.yaml")
    assert data.get("window_days") == WINDOW_DAYS, f"window_days là {WINDOW_DAYS}"
    slos = data.get("slos")
    assert isinstance(slos, list) and len(slos) >= 4, "slos là danh sách ít nhất 4 SLO"
    names = [s.get("name") for s in slos if isinstance(s, dict)]
    assert len(names) == len(slos) and len(set(names)) == len(names), "mỗi SLO là mapping có name, không trùng"
    missing = sorted(SLO_NAMES - set(names))
    assert not missing, f"thiếu SLO {missing}"
    for slo in slos:
        name = slo["name"]
        assert slo.get("kind") in KINDS, f"{name}: kind thuộc {sorted(KINDS)}"
        assert words(slo.get("sli")) >= 6, f"{name}: sli là câu định nghĩa ≥6 từ"
        assert isinstance(slo.get("measured_at"), str) and slo["measured_at"].strip(), f"{name}: measured_at không rỗng"
        target = slo.get("target")
        assert isinstance(target, float) and 0 < target < 1, f"{name}: target là số thực trong (0, 1)"
        if slo["kind"] == "time":
            expected = (1 - target) * WINDOW_DAYS * 1440
            value = slo.get("budget_minutes")
            ok = isinstance(value, (int, float)) and math.isclose(value, expected, rel_tol=0.01)
            assert ok, f"{name}: budget_minutes = (1 - target) × số phút của cửa sổ (sai số 1%)"
    by_name = {s["name"]: s for s in slos}
    assert by_name["quality"]["kind"] == "events" and by_name["quality"]["target"] == QUALITY_TARGET, \
        f"quality: kind events, target {QUALITY_TARGET} như đã thống nhất với đội sản phẩm"
    assert by_name["freshness"]["kind"] == "time" and by_name["freshness"]["target"] == FRESHNESS_TARGET, \
        f"freshness: kind time, target {FRESHNESS_TARGET}"
    groups = (data.get("prometheus") or {}).get("groups")
    assert isinstance(groups, list) and groups, "prometheus.groups là danh sách rule group của Prometheus"


def test_m18_slo_budget_matches_data(project, incident):
    data = load_yaml("reports", "senior", "slo.yaml")
    quality = next((s for s in data.get("slos") or [] if isinstance(s, dict) and s.get("name") == "quality"), {})
    budget = quality.get("budget_events")
    truth = incident()
    complete = isinstance(budget, dict) and set(budget) == set(truth["requests_day"])
    assert complete, f"quality.budget_events là mapping market → số, đủ {sorted(truth['requests_day'])}"
    allowed = {m: (1 - QUALITY_TARGET) * WINDOW_DAYS * n for m, n in truth["requests_day"].items()}
    wrong = [m for m, n in allowed.items() if not (isinstance(budget[m], (int, float)) and math.isclose(budget[m], n, rel_tol=0.01))]
    assert not wrong, f"quality.budget_events lệch quá 1% ở {len(wrong)} market"


def slo_rules(data: dict) -> list[dict]:
    return [r for g in (data.get("prometheus") or {}).get("groups") or [] if isinstance(g, dict) for r in g.get("rules") or []]


def write_rules(tmp_path, data: dict) -> str:
    (tmp_path / "slo.rules.yml").write_text(yaml.safe_dump({"groups": data["prometheus"]["groups"]}, sort_keys=False),
                                            encoding="utf-8")
    return "slo.rules.yml"


def seconds(text) -> int:
    assert re.fullmatch(r"(\d+[smh])+", str(text)), f"thời lượng không hợp lệ: {text!r}"
    return sum(int(n) * {"s": 1, "m": 60, "h": 3600}[unit] for n, unit in re.findall(r"(\d+)([smh])", str(text)))


def test_m18_rules_metadata(project, tmp_path):
    data = load_yaml("reports", "senior", "slo.yaml")
    alerts = {}
    for rule in slo_rules(data):
        if "alert" in rule:
            assert rule["alert"] not in alerts, f"trùng alert {rule['alert']}"
            alerts[rule["alert"]] = rule
    missing = sorted(set(ALERTS) - set(alerts))
    assert not missing, f"thiếu alert {missing}"
    for name, (severity, max_for) in ALERTS.items():
        rule = alerts[name]
        assert rule.get("labels", {}).get("severity") == severity, f"{name}: severity {severity}"
        assert seconds(rule.get("for", "0s")) <= max_for, f"{name}: for tối đa {max_for // 60} phút"
        assert str(rule.get("annotations", {}).get("summary", "")).strip(), f"{name}: cần annotations.summary"
        assert str(rule.get("annotations", {}).get("runbook_url", "")).startswith("https://"), f"{name}: runbook_url https://"
        assert "market" in rule["expr"], f"{name}: biểu thức phải giữ nhãn market"
    for name in BURN_ALERTS:
        assert re.search(r"\band\b", alerts[name]["expr"]), f"{name}: cần hai cửa sổ nối bằng and"
    result = mlopskit.promtool("check", "rules", write_rules(tmp_path, data), cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def counter(segments) -> str:
    values, total = [0], 0
    for per_step, steps in segments:
        for _ in range(steps):
            total += per_step
            values.append(total)
    return " ".join(str(v) for v in values)


def market_quality(market: str, good: int, bad: int, steps: int, stop: int | None = None) -> list[tuple[str, str]]:
    def series(per):
        if stop is None:
            return counter([(per, steps)])
        return counter([(per, stop)]) + " stale"
    return [(QUALITY.format(market, "good"), series(good)), (QUALITY.format(market, "bad"), series(bad)),
            (REQUESTS.format(market), counter([(good + bad, steps)]))]


def market_segments(market: str, good, bad) -> list[tuple[str, str]]:
    total = [(g + b, n) for (g, n), (b, _) in zip(good, bad)]
    return [(QUALITY.format(market, "good"), counter(good)), (QUALITY.format(market, "bad"), counter(bad)),
            (REQUESTS.format(market), counter(total))]


def stall(start: int, end: int, total: int) -> str:
    return " ".join(str(start * 60 if start <= m < end else m * 60) for m in range(total + 1))


def firing(name: str, at: str, markets: list[str]) -> dict:
    return {"expr": f'count by (market) (ALERTS{{alertname="{name}",alertstate="firing"}})', "eval_time": at,
            "exp_samples": [{"labels": f'{{market="{m}"}}', "value": 1} for m in sorted(markets)]}


def run_scenarios(tmp_path, data: dict, tests: list[dict]):
    rules = write_rules(tmp_path, data)
    spec = {"rule_files": [rules], "evaluation_interval": "1m", "tests": tests}
    (tmp_path / "tests.yml").write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    return mlopskit.promtool("test", "rules", "tests.yml", cwd=tmp_path, timeout=300)


def test_m18_rules_burn_per_market(project, tmp_path):
    data = load_yaml("reports", "senior", "slo.yaml")
    steps = 600
    heavy = (market_quality("queens", 40, 60, steps) + market_quality("manhattan", 95, 5, steps)
             + market_quality("brooklyn", 92, 8, steps))
    moderate = market_quality("queens", 70, 30, steps) + market_quality("manhattan", 95, 5, steps)
    quiet = market_quality("queens", 92, 8, steps) + market_quality("manhattan", 95, 5, steps)
    missing = market_quality("queens", 95, 5, steps, stop=180) + market_quality("manhattan", 95, 5, steps)
    spike = market_segments("queens", [(95, 360), (60, 45)], [(5, 360), (40, 45)]) + market_quality("manhattan", 95, 5, 405)
    recovery = market_segments("queens", [(30, 180), (98, 60)], [(70, 180), (2, 60)]) + market_quality("manhattan", 95, 5, 240)
    fresh = [(FRESHNESS.format("queens"), stall(60, 100, 200)), (FRESHNESS.format("brooklyn"), stall(60, 78, 200)),
             (FRESHNESS.format("manhattan"), stall(0, 0, 200))]
    tests = [
        {"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in heavy], "promql_expr_test": [
            firing("ETAMarketQualityFastBurn", "2h", ["queens"]), firing("ETAMarketQualitySlowBurn", "8h", ["queens"]),
            firing("ETAMarketLabelsMissing", "8h", [])]},
        {"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in moderate], "promql_expr_test": [
            firing("ETAMarketQualityFastBurn", "8h", []), firing("ETAMarketQualitySlowBurn", "8h", ["queens"])]},
        {"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in quiet], "promql_expr_test": [
            firing("ETAMarketQualityFastBurn", "8h", []), firing("ETAMarketQualitySlowBurn", "8h", []),
            firing("ETAMarketLabelsMissing", "8h", [])]},
        {"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in missing], "promql_expr_test": [
            firing("ETAMarketLabelsMissing", "4h", []), firing("ETAMarketLabelsMissing", "6h", ["queens"]),
            firing("ETAMarketQualityFastBurn", "6h", [])]},
        {"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in spike], "promql_expr_test": [
            firing("ETAMarketQualitySlowBurn", "405m", []), firing("ETAMarketQualityFastBurn", "405m", [])]},
        {"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in recovery], "promql_expr_test": [
            firing("ETAMarketQualityFastBurn", "175m", ["queens"]), firing("ETAMarketQualityFastBurn", "190m", [])]},
        {"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in fresh], "promql_expr_test": [
            firing("ETAMarketFeatureStale", "70m", []), firing("ETAMarketFeatureStale", "79m", []),
            firing("ETAMarketFeatureStale", "97m", ["queens"]),
            firing("ETAMarketFeatureStale", "120m", [])]},
    ]
    result = run_scenarios(tmp_path, data, tests)
    assert result.returncode == 0, result.stdout + result.stderr


def incident_series(truth) -> list[tuple[str, str]]:
    trips, fresh = truth["trips"], truth["freshness"]
    arrived = ((trips["label_ts"] - trips["ts"].dt.normalize()).dt.total_seconds() // 60).astype(int).clip(upper=1439)
    asked = ((trips["ts"] - trips["ts"].dt.normalize()).dt.total_seconds() // 60).astype(int)
    out = []
    for market in sorted(trips["market"].unique()):
        mask = trips["market"] == market
        for outcome, flag in (("good", False), ("bad", True)):
            per = arrived[mask & (trips["bad"] == flag)].value_counts().reindex(range(1440), fill_value=0).cumsum()
            out.append((QUALITY.format(market, outcome), "0 " + " ".join(str(v) for v in per)))
        per = asked[mask].value_counts().reindex(range(1440), fill_value=0).cumsum()
        out.append((REQUESTS.format(market), "0 " + " ".join(str(v) for v in per)))
        ages = fresh.loc[fresh["market"] == market, "age_s"].to_list()
        out.append((FRESHNESS.format(market), " ".join(str(m * 60 - a) for m, a in enumerate(ages))))
    return out


def test_m18_rules_on_incident(project, tmp_path, incident):
    data = load_yaml("reports", "senior", "slo.yaml")
    truth = incident()
    assert truth["affected"], "Dữ liệu sự cố không có khung tệp nào: tệp nguồn đổi, tải lại nyc-tlc"
    markets = sorted(truth["requests_day"])
    late = minutes(truth["mitigated_at"]) + 30
    stale_at = minutes(truth["started_at"]) + 10
    checks = [firing("ETAMarketFeatureStale", f"{stale_at}m", truth["affected"]),
              firing("ETAMarketQualityFastBurn", f"{late}m", truth["affected"])]
    for at in ("6h", "622m", "11h", "20h"):
        checks += [firing(name, at, []) for name in ALERTS]
    tests = [{"interval": "1m", "input_series": [{"series": s, "values": v} for s, v in incident_series(truth)],
              "promql_expr_test": checks}]
    result = run_scenarios(tmp_path, data, tests)
    failed = len(re.findall(r"expr: ", result.stdout + result.stderr))
    detail = "" if failed else f"\npromtool không chạy được các kiểm tra:\n{result.stderr}"
    assert result.returncode == 0, (
        f"rule chưa bắn đúng trên dữ liệu sự cố: {failed} kiểm tra sai trên {len(checks)} "
        f"(có {len(markets)} market; xem mục 3 của đề về các ca được kiểm){detail}")


def test_m18_postmortem(project):
    path = require_file("docs", "senior", "postmortem.md")
    text = path.read_text(encoding="utf-8")
    incident_record = load_yaml("reports", "senior", "incident.yaml")
    found = heading_texts(text)
    missing = [h for h in POSTMORTEM_HEADINGS if not has_heading(found, h)]
    assert not missing, f"postmortem.md thiếu heading {missing}"
    assert "TODO" not in text and len(text.split()) >= 600, "postmortem.md cần ít nhất 600 từ, không còn TODO"
    lowered = text.lower()
    named = sum(bool(re.search(rf"(?<!\w){re.escape(h)}(?!\w)", lowered)) for h in incident_facts()["people"])
    assert named == 0, f"postmortem nhắc {named} người trong kênh chat bằng tên: dùng vai trò"
    blamed = sum(phrase in lowered for phrase in BLAME)
    assert blamed == 0, f"postmortem có {blamed} cụm đổ lỗi cho người (mục 6 của đề)"
    impact_text = section(text, "Tác động")
    impact = incident_record.get("impact") or {}
    absent = [k for k in IMPACT_INT if not (isinstance(impact.get(k), int) and integer_in(impact_text, impact[k]))]
    assert not absent, f"phần Tác động cần các số của incident.yaml: thiếu {absent}"
    header, rows = table(section(text, "Dòng thời gian"))
    assert header[:2] == ["thời điểm", "sự kiện"], "Dòng thời gian: bảng cột Thời điểm, Sự kiện"
    times = [r[0] for r in rows if r and TIME.match(r[0]) and len(r) > 1 and r[1]]
    assert len(times) >= 10 and times == sorted(times), "Dòng thời gian: ít nhất 10 mốc HH:MM có mô tả, tăng dần"
    marks = [incident_record.get(k) for k in ("started_at", "detected_at", "mitigated_at")]
    assert all(m in times for m in marks), "Dòng thời gian phải có mốc started_at, detected_at, mitigated_at của incident.yaml"
    causes_text = section(text, "Nguyên nhân")
    unexplained = [c for c in incident_record.get("causes") or [] if isinstance(c, str) and c not in causes_text]
    assert not unexplained, f"phần Nguyên nhân cần giải thích từng nhãn trong causes: thiếu {unexplained}"
    assert len(bullets(section(text, "Điều làm tốt"))) >= 2, "Điều làm tốt: ít nhất 2 gạch đầu dòng"
    header, rows = table(section(text, "Hành động"))
    assert header[:5] == ["hành động", "loại", "chủ sở hữu", "hạn", "cách kiểm"], \
        "Hành động: bảng cột Hành động, Loại, Chủ sở hữu, Hạn, Cách kiểm"
    rows = [r for r in rows if len(r) >= 5]
    assert len(rows) >= 5 and all(all(r[:5]) for r in rows), "Hành động: ít nhất 5 dòng, không ô trống"
    kinds = {r[1].lower() for r in rows}
    same = kinds == ACTION_KINDS
    assert same, f"Hành động: Loại chỉ gồm và có đủ {sorted(ACTION_KINDS)}"
    assert all(DATE.match(r[3]) for r in rows), "Hành động: Hạn dạng YYYY-MM-DD"


def design_problems(doc: str, slo_names: list[str]) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("còn TODO")
    for n in range(1, DESIGN_SECTIONS + 1):
        if not re.search(rf"^## {n}\. ", doc, re.M):
            found.append(f"thiếu phần '## {n}.'")
    s1 = numbered(doc, 1)
    header, rows = table(s1)
    if header[:2] != ["yêu cầu", "con số"] or len([r for r in rows if len(r) >= 2 and re.search(r"\d", r[1])]) < 6:
        found.append("phần 1: bảng Yêu cầu, Con số với ít nhất 6 dòng có số")
    if "ngoài phạm vi" not in s1.lower() or len(bullets(s1)) < 2:
        found.append("phần 1: ngoài phạm vi với ít nhất 2 gạch đầu dòng")
    header, rows = table(numbered(doc, 2))
    if header[:3] != ["market", "request/ngày", "đỉnh request/phút"] or len([r for r in rows if len(r) >= 3]) < 4:
        found.append("phần 2: bảng Market, Request/ngày, Đỉnh request/phút với ít nhất 4 dòng")
    s3 = numbered(doc, 3)
    if "reports/senior/slo.yaml" not in s3 or any(n not in s3 for n in slo_names):
        found.append("phần 3: dẫn reports/senior/slo.yaml và nhắc mọi SLO trong đó")
    s4 = numbered(doc, 4)
    diagram = re.search(r"```mermaid\n(.*?)```", s4, re.S)
    if not diagram or len(re.findall(r"-->|-\.->|==>", diagram.group(1))) < 10 or "market" not in diagram.group(1).lower():
        found.append("phần 4: khối mermaid ít nhất 10 cạnh, có thành phần theo market")
    if len(prose(s4)) < 300:
        found.append("phần 4: ít nhất 300 ký tự giải thích ngoài sơ đồ và bảng")
    if len(bullets(numbered(doc, 5))) < 3:
        found.append("phần 5: ít nhất 3 gạch đầu dòng")
    if len(re.findall(r"^\s*\d+\.\s+\S", numbered(doc, 6), re.M)) < 5:
        found.append("phần 6: ít nhất 5 bước đánh số")
    header, rows = table(numbered(doc, 7))
    rows = [r for r in rows if len(r) >= 5]
    if header[:5] != ["phương án", "chi phí", "độ trễ", "chất lượng", "chọn"] or len(rows) < 3 \
            or sum(r[4].lower() == "có" for r in rows) != 1:
        found.append("phần 7: bảng Phương án, Chi phí, Độ trễ, Chất lượng, Chọn; ít nhất 3 dòng, đúng một 'có'")
    if len([b for b in bullets(numbered(doc, 8)) if re.search(r"\d", b)]) < 4:
        found.append("phần 8: ít nhất 4 gạch đầu dòng có số")
    s9 = numbered(doc, 9)
    header, rows = table(s9)
    rows = [r for r in rows if len(r) >= 4]
    if header[:4] != ["hỏng", "phát hiện", "giảm thiểu", "phạm vi"] or len(rows) < 6 or any(not all(r[:4]) for r in rows):
        found.append("phần 9: bảng Hỏng, Phát hiện, Giảm thiểu, Phạm vi; ít nhất 6 dòng, không ô trống")
    if "fallback" not in s9.lower() or "postmortem.md" not in s9:
        found.append("phần 9: có fallback và dẫn postmortem.md")
    s10 = numbered(doc, 10).lower()
    if len(bullets(s10)) < 4 or "canary" not in s10 or "rollback" not in s10 or "freshness" not in s10:
        found.append("phần 10: ít nhất 4 gạch đầu dòng, có canary, rollback, freshness")
    if len([b for b in bullets(numbered(doc, 11)) if b.strip().endswith("?")]) < 5:
        found.append("phần 11: ít nhất 5 câu hỏi kết thúc bằng '?'")
    return found


def slo_names() -> list[str]:
    data = load_yaml("reports", "senior", "slo.yaml")
    return [s["name"] for s in data.get("slos") or [] if isinstance(s, dict) and isinstance(s.get("name"), str)]


def test_m18_design_doc(project):
    doc = require_file("docs", "senior", "design-doc.md").read_text(encoding="utf-8")
    assert len(doc.split()) >= 1200, "design-doc.md cần ít nhất 1 200 từ"
    found = design_problems(doc, slo_names())
    assert not found, f"design-doc.md còn {len(found)} mục chưa đạt:\n" + "\n".join(found)


def test_m18_design_doc_traffic(project, incident):
    doc = require_file("docs", "senior", "design-doc.md").read_text(encoding="utf-8")
    truth = incident()
    _, rows = table(numbered(doc, 2))
    by_market = {r[0].strip("` ").lower(): r for r in rows if len(r) >= 3}
    wrong = 0
    for market, count in truth["requests_day"].items():
        row = by_market.get(market)
        if row is None or not integer_in(row[1], count) or not integer_in(row[2], truth["peak_minute"][market]):
            wrong += 1
    assert wrong == 0, f"phần 2: {wrong} market thiếu dòng hoặc số request/ngày, đỉnh request/phút chưa khớp dữ liệu sự cố"
