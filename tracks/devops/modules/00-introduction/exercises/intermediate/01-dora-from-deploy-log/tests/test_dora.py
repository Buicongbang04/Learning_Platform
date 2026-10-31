from datetime import datetime, timedelta, timezone

import pytest

from testkit import Exercise

ex = Exercise(__file__)
ICT = timezone(timedelta(hours=7))
START = datetime(2026, 10, 1, tzinfo=ICT)
END = datetime(2026, 10, 8, tzinfo=ICT)
EMPTY_START = datetime(2026, 11, 1, tzinfo=timezone.utc)
EMPTY_END = datetime(2026, 11, 8, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def dora():
    return ex.module("dora.py")


@pytest.fixture(scope="module")
def log(dora):
    load = dora.load_jsonl
    return {
        "deploys": load(ex.fixtures / "deploys.jsonl"),
        "commits": load(ex.fixtures / "commits.jsonl"),
        "incidents": load(ex.fixtures / "incidents.jsonl"),
    }


def test_parse_ts_normalises_offsets(dora):
    a = dora.parse_ts("2026-10-02T03:15:00Z")
    b = dora.parse_ts("2026-10-02T10:15:00+07:00")
    assert a == b
    assert a.utcoffset() == timedelta(0)
    assert b.utcoffset() == timedelta(0)


def test_parse_ts_rejects_naive(dora):
    with pytest.raises(ValueError):
        dora.parse_ts("2026-10-02T10:15:00")


def test_counted_deploys_rules(dora, log):
    ids = [d["id"] for d in dora.counted_deploys(log["deploys"], START, END)]
    assert ids == ["d00", "d01", "d03", "d05", "d07", "d08", "d09", "d10", "d11"]


def test_window_uses_instants_not_date_strings(dora, log):
    ids = {d["id"] for d in dora.counted_deploys(log["deploys"], START, END)}
    assert "d00" in ids
    assert "d12" not in ids


def test_deployment_frequency(dora, log):
    assert dora.deployment_frequency(log["deploys"], START, END) == pytest.approx(9 / 7)


def test_rollback_marks_failed_change_and_is_not_a_deploy(dora, log):
    failed = dora.failed_change_ids(log["deploys"], log["incidents"], START, END)
    assert failed == {"d05", "d08"}


def test_change_failure_rate_counts_each_change_once(dora, log):
    assert dora.change_failure_rate(log["deploys"], log["incidents"], START, END) == pytest.approx(2 / 9)


def test_lead_time_per_commit(dora, log):
    lt = dora.lead_times(log["deploys"], log["commits"], START, END)
    assert lt["c00"] == timedelta(hours=3)
    assert lt["c01"] == timedelta(hours=13, minutes=30)
    assert lt["c03"] == timedelta(hours=25, minutes=15)
    assert lt["c07"] == timedelta(hours=1, minutes=10)
    assert lt["c09"] == timedelta(minutes=35)


def test_lead_time_ignores_rolled_back_deploy(dora, log):
    lt = dora.lead_times(log["deploys"], log["commits"], START, END)
    assert lt["c04"] == timedelta(hours=47)
    assert lt["c05"] == timedelta(hours=25)


def test_lead_time_skips_unknown_and_out_of_window_commits(dora, log):
    lt = dora.lead_times(log["deploys"], log["commits"], START, END)
    assert set(lt) == {"c00", "c01", "c02", "c03", "c04", "c05", "c06", "c07", "c09"}


def test_median_lead_time(dora, log):
    assert dora.median_lead_time(log["deploys"], log["commits"], START, END) == timedelta(hours=3)


def test_recovery_spans_midnight_and_takes_last_restore_event(dora, log):
    rt = dora.recovery_times(log["deploys"], log["incidents"], START, END)
    assert rt == {"d05": timedelta(minutes=30), "d08": timedelta(hours=2, minutes=10)}


def test_median_recovery_time(dora, log):
    assert dora.median_recovery_time(log["deploys"], log["incidents"], START, END) == timedelta(minutes=80)


def test_unresolved_incident_counts_as_failure_but_not_recovery(dora):
    deploys = [
        {"id": "x1", "env": "production", "status": "success", "finished_at": "2026-10-01T10:00:00Z", "commits": [], "rollback_of": None},
        {"id": "x2", "env": "production", "status": "success", "finished_at": "2026-10-02T10:00:00Z", "commits": [], "rollback_of": None},
    ]
    incidents = [{"id": "j1", "caused_by_deploy": "x2", "started_at": "2026-10-02T10:30:00Z", "resolved_at": None}]
    assert dora.change_failure_rate(deploys, incidents, START, END) == pytest.approx(0.5)
    assert dora.recovery_times(deploys, incidents, START, END) == {}
    assert dora.median_recovery_time(deploys, incidents, START, END) is None


def test_empty_window(dora, log):
    d, c, i = log["deploys"], log["commits"], log["incidents"]
    assert dora.deployment_frequency(d, EMPTY_START, EMPTY_END) == 0.0
    assert dora.change_failure_rate(d, i, EMPTY_START, EMPTY_END) is None
    assert dora.median_lead_time(d, c, EMPTY_START, EMPTY_END) is None
    assert dora.median_recovery_time(d, i, EMPTY_START, EMPTY_END) is None


def test_invalid_window(dora, log):
    with pytest.raises(ValueError):
        dora.deployment_frequency(log["deploys"], END, START)


def test_naive_timestamp_in_log_is_rejected(dora):
    deploys = [{"id": "n1", "env": "production", "status": "success", "finished_at": "2026-10-02T10:00:00", "commits": [], "rollback_of": None}]
    with pytest.raises(ValueError):
        dora.counted_deploys(deploys, START, END)


def test_report(dora, log):
    report = dora.dora_report(log["deploys"], log["commits"], log["incidents"], START, END)
    assert report == {
        "deploys_per_week": pytest.approx(9.0),
        "change_failure_rate": pytest.approx(2 / 9),
        "median_lead_time_hours": pytest.approx(3.0),
        "median_recovery_hours": pytest.approx(80 / 60),
    }


def test_report_empty_window(dora, log):
    report = dora.dora_report(log["deploys"], log["commits"], log["incidents"], EMPTY_START, EMPTY_END)
    assert report == {
        "deploys_per_week": 0.0,
        "change_failure_rate": None,
        "median_lead_time_hours": None,
        "median_recovery_hours": None,
    }
