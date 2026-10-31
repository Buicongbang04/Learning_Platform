from datetime import datetime, timedelta, timezone

import pytest

from testkit import Exercise

ex = Exercise(__file__)
ICT = timezone(timedelta(hours=7))
START = datetime(2026, 10, 1, tzinfo=ICT)
END = datetime(2026, 10, 31, tzinfo=ICT)
UTC = timezone.utc


def at(day: int, hour: int, minute: int = 0, tz=ICT) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=tz)


def incident(started: str, resolved: str | None, impact: str = "outage", id_: str = "i") -> dict:
    return {"id": id_, "started_at": started, "resolved_at": resolved, "impact": impact}


@pytest.fixture(scope="module")
def av():
    return ex.module("availability.py")


@pytest.mark.parametrize(
    "slo,window,expected",
    [
        (0.999, timedelta(days=30), timedelta(minutes=43, seconds=12)),
        (0.9999, timedelta(days=30), timedelta(minutes=4, seconds=19.2)),
        (0.995, timedelta(days=7), timedelta(minutes=50, seconds=24)),
        (0.99, timedelta(days=365), timedelta(days=3, hours=15, minutes=36)),
    ],
)
def test_allowed_downtime(av, slo, window, expected):
    assert abs(av.allowed_downtime(slo, window) - expected) < timedelta(milliseconds=1)


@pytest.mark.parametrize("slo", [0.0, 1.0, 99.9, -0.5])
def test_allowed_downtime_rejects_bad_slo(av, slo):
    with pytest.raises(ValueError):
        av.allowed_downtime(slo, timedelta(days=30))


def test_merge_overlapping_nested_and_touching(av):
    spans = [
        (at(3, 10), at(3, 11)),
        (at(1, 9), at(1, 10)),
        (at(1, 9, 30), at(1, 10, 30)),
        (at(3, 10, 15), at(3, 10, 45)),
        (at(3, 11), at(3, 11, 20)),
    ]
    assert av.merge_outages(spans) == [(at(1, 9), at(1, 10, 30)), (at(3, 10), at(3, 11, 20))]


def test_merge_empty(av):
    assert av.merge_outages([]) == []


def test_downtime_merges_duplicate_alerts(av):
    incidents = [
        incident("2026-10-05T10:00:00+07:00", "2026-10-05T10:30:00+07:00", id_="api"),
        incident("2026-10-05T03:10:00Z", "2026-10-05T03:40:00Z", id_="worker"),
    ]
    assert av.downtime(incidents, START, END) == timedelta(minutes=40)


def test_downtime_spans_midnight_with_mixed_offsets(av):
    incidents = [incident("2026-10-10T23:30:00+07:00", "2026-10-10T17:15:00Z")]
    assert av.downtime(incidents, START, END) == timedelta(minutes=45)


def test_downtime_ignores_degraded(av):
    incidents = [
        incident("2026-10-05T10:00:00+07:00", "2026-10-05T12:00:00+07:00", impact="degraded"),
        incident("2026-10-06T10:00:00+07:00", "2026-10-06T10:05:00+07:00"),
    ]
    assert av.downtime(incidents, START, END) == timedelta(minutes=5)


def test_downtime_clips_to_window(av):
    incidents = [
        incident("2026-09-30T23:00:00+07:00", "2026-10-01T00:20:00+07:00"),
        incident("2026-10-30T23:50:00+07:00", "2026-10-31T02:00:00+07:00"),
        incident("2026-09-20T00:00:00+07:00", "2026-09-20T05:00:00+07:00"),
    ]
    assert av.downtime(incidents, START, END) == timedelta(minutes=30)


def test_unresolved_outage_runs_to_window_end(av):
    incidents = [incident("2026-10-30T22:00:00+07:00", None)]
    assert av.downtime(incidents, START, END) == timedelta(hours=2)

    later = [incident("2026-11-02T08:00:00+07:00", None)]
    assert av.downtime(later, START, END) == timedelta(0)


def test_naive_timestamp_rejected(av):
    with pytest.raises(ValueError):
        av.downtime([incident("2026-10-05T10:00:00", "2026-10-05T10:30:00")], START, END)


def test_resolved_before_started_rejected(av):
    with pytest.raises(ValueError):
        av.downtime([incident("2026-10-05T10:30:00+07:00", "2026-10-05T10:00:00+07:00")], START, END)


def test_availability(av):
    incidents = [incident("2026-10-05T10:00:00+07:00", "2026-10-05T10:43:12+07:00")]
    assert av.availability(incidents, START, END) == pytest.approx(1 - 43.2 / (30 * 24 * 60))


def test_no_incidents_is_full_availability(av):
    assert av.downtime([], START, END) == timedelta(0)
    assert av.availability([], START, END) == 1.0


def test_budget_remaining_can_go_negative(av):
    incidents = [incident("2026-10-05T10:00:00+07:00", "2026-10-05T11:00:00+07:00")]
    remaining = av.budget_remaining(0.999, incidents, START, END)
    assert remaining == timedelta(minutes=43, seconds=12) - timedelta(hours=1)
    assert remaining < timedelta(0)
