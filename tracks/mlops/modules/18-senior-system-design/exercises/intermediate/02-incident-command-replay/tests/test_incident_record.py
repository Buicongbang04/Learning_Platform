import csv
import functools
import re
from pathlib import Path

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
MONTHLY_REQUESTS = 43_200_000
SLO = 0.995
START_RATIO = 0.02
CLEAR_RATIO = 0.01
DECISIONS = {"rollback", "restart", "scale-out", "wait", "disable-feature"}
DEPLOY = re.compile(r'^(\S+)T(\d\d:\d\d):\d\dZ deploy_id=(\S+) service=(\S+) change="([^"]*)"')
CHAT = re.compile(r"^(\d\d:\d\d) @(\w+): (.*)$")
TIME = re.compile(r"^\d\d:\d\d$")


def minutes(hhmm):
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


@pytest.fixture(scope="module")
def record():
    data = yaml.safe_load(ex.read("incident.yaml"))
    assert isinstance(data, dict), "incident.yaml phải là một mapping"
    return data


@functools.cache
def truth():
    rows = list(csv.DictReader((FIXTURES / "metrics.csv").open(encoding="utf-8")))
    ratio = [int(r["errors_5xx"]) / int(r["requests"]) for r in rows]
    start = next(i for i, x in enumerate(ratio) if x > START_RATIO)
    clear = next(i for i in range(start, len(rows)) if all(x <= CLEAR_RATIO for x in ratio[i:]))
    failed = sum(int(r["errors_5xx"]) for r in rows[start:clear])
    alert = next(line.split()[0][11:16] for line in (FIXTURES / "alerts.log").read_text(encoding="utf-8").splitlines()
                 if " firing " in line and "service=eta-service" in line)
    deploys = [DEPLOY.match(line).groups() for line in (FIXTURES / "deploys.log").read_text(encoding="utf-8").splitlines()]
    started_at, mitigated_at = rows[start]["minute"], rows[clear]["minute"]
    service = [d for d in deploys if d[3] == "eta-service"]
    trigger = [d for d in service if d[1] <= started_at][-1]
    before, _, after = trigger[4].split()[-3:]
    reverse = f"{after} -> {before}"
    undo = [d for d in service if started_at < d[1] <= mitigated_at and d[4].endswith(reverse)]
    chat = [CHAT.match(line).groups() for line in (FIXTURES / "chat.log").read_text(encoding="utf-8").splitlines()]
    roles = {
        "incident_commander": next(who for _, who, text in chat if text.startswith("nhận vai trò IC")),
        "comms": next(who for _, who, text in chat if text.startswith("nhận comms")),
        "ops": next(who for _, who, text in chat if undo and text.startswith(f"đã chạy {undo[0][2]}")),
    }
    pct = failed / (MONTHLY_REQUESTS * (1 - SLO)) * 100
    severity = "SEV1" if pct >= 10 or max(ratio) >= 0.5 else "SEV2" if pct >= 2 else "SEV3"
    return {
        "started_at": started_at, "mitigated_at": mitigated_at, "detected_at": alert, "failed": failed, "pct": pct,
        "trigger": trigger[2], "decision": "rollback" if undo else None, "roles": roles, "severity": severity,
    }


def test_no_placeholders_left():
    assert "TODO" not in ex.read("incident.yaml")


@pytest.mark.parametrize("field", ["started_at", "detected_at", "mitigated_at"])
def test_times_are_quoted_hhmm(record, field):
    value = record.get(field)
    assert isinstance(value, str), f"{field}: viết thời điểm trong ngoặc kép, vd. \"09:30\""
    assert TIME.match(value), f"{field}: dạng HH:MM"


@pytest.mark.parametrize("field", ["started_at", "detected_at", "mitigated_at"])
def test_times_match_the_evidence(record, field):
    matches = record.get(field) == truth()[field]
    assert matches, f"{field} chưa khớp dữ liệu sự cố"


def test_durations_are_consistent(record):
    started, detected, mitigated = (minutes(str(record[k])) for k in ("started_at", "detected_at", "mitigated_at"))
    assert record.get("time_to_detect_min") == detected - started
    assert record.get("time_to_mitigate_min") == mitigated - started


def test_impact_is_measured(record):
    impact = record.get("impact") or {}
    failed = impact.get("failed_requests")
    pct = impact.get("budget_consumed_pct")
    failed_ok = isinstance(failed, int) and failed == truth()["failed"]
    assert failed_ok, "failed_requests chưa khớp metrics.csv"
    pct_ok = isinstance(pct, (int, float)) and abs(pct - truth()["pct"]) <= 0.05
    assert pct_ok, "budget_consumed_pct chưa khớp"


def test_severity_follows_the_table(record):
    assert record.get("severity") in {"SEV1", "SEV2", "SEV3"}
    matches = record.get("severity") == truth()["severity"]
    assert matches, "severity chưa khớp bảng phân loại"


def test_trigger_and_decision(record):
    assert record.get("decision") in DECISIONS
    trigger_ok = record.get("trigger") == truth()["trigger"]
    assert trigger_ok, "trigger chưa khớp"
    decision_ok = record.get("decision") == truth()["decision"]
    assert decision_ok, "decision chưa phải hành động đã chấm dứt tác động"


def test_roles_match_the_incident_channel(record):
    roles = record.get("roles") or {}
    assert set(roles) == {"incident_commander", "comms", "ops"}
    assert len({str(v) for v in roles.values()}) == 3, "ba vai trò phải do ba người giữ"
    roles_ok = {k: str(v).lstrip("@") for k, v in roles.items()} == truth()["roles"]
    assert roles_ok, "vai trò chưa khớp kênh sự cố"


def test_next_steps_are_listed(record):
    steps = record.get("next_steps") or []
    assert isinstance(steps, list) and len([s for s in steps if str(s).strip()]) >= 3


def test_truth_is_derived_from_the_fixtures():
    derived = truth()
    assert derived["decision"] in DECISIONS
    assert minutes(derived["started_at"]) < minutes(derived["detected_at"]) < minutes(derived["mitigated_at"])
    assert len(set(derived["roles"].values())) == 3
