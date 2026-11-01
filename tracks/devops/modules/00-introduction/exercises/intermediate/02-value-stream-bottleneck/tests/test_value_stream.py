import json
from datetime import timedelta

import pytest

from testkit import Exercise

ex = Exercise(__file__)
H = timedelta(hours=1)


@pytest.fixture(scope="module")
def vs():
    return ex.module("value_stream.py")


@pytest.fixture(scope="module")
def changes():
    lines = (ex.fixtures / "changes.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def by_id(changes, cid):
    return next(c for c in changes if c["id"] == cid)


def test_stage_durations(vs, changes):
    assert vs.stage_durations(by_id(changes, "PR-101")) == {
        "coding": 6 * H,
        "review_wait": 20 * H,
        "review": 2 * H,
        "merge_wait": 1 * H,
        "deploy_wait": 3 * H,
    }


def test_stage_durations_across_offsets_and_midnight(vs, changes):
    assert vs.stage_durations(by_id(changes, "PR-105")) == {
        "coding": 8 * H,
        "review_wait": 22 * H,
        "review": 4 * H,
        "merge_wait": 0.5 * H,
        "deploy_wait": 2 * H,
    }


def test_self_merged_change_has_zero_review(vs, changes):
    assert vs.stage_durations(by_id(changes, "PR-106")) == {
        "coding": 1 * H,
        "review_wait": timedelta(0),
        "review": timedelta(0),
        "merge_wait": 0.25 * H,
        "deploy_wait": 0.5 * H,
    }


def test_stage_durations_reject_wip(vs, changes):
    with pytest.raises(ValueError):
        vs.stage_durations(by_id(changes, "PR-108"))


def test_stage_durations_reject_out_of_order(vs, changes):
    broken = dict(by_id(changes, "PR-101"), merged_at="2026-10-06T12:00:00+07:00")
    with pytest.raises(ValueError):
        vs.stage_durations(broken)


def test_stage_durations_reject_half_review(vs, changes):
    broken = dict(by_id(changes, "PR-101"), approved_at=None)
    with pytest.raises(ValueError):
        vs.stage_durations(broken)


def test_stage_durations_reject_naive(vs, changes):
    broken = dict(by_id(changes, "PR-101"), deployed_at="2026-10-06T17:00:00")
    with pytest.raises(ValueError):
        vs.stage_durations(broken)


def test_completed_excludes_wip(vs, changes):
    assert [c["id"] for c in vs.completed_changes(changes)] == [f"PR-10{i}" for i in range(1, 8)]


def test_unreviewed(vs, changes):
    assert vs.unreviewed(changes) == ["PR-106"]


def test_stage_medians(vs, changes):
    assert vs.stage_medians(changes) == {
        "coding": 5 * H,
        "review_wait": 20 * H,
        "review": 2 * H,
        "merge_wait": 1 * H,
        "deploy_wait": 3 * H,
    }


def test_bottleneck_uses_median_not_mean(vs, changes):
    assert vs.bottleneck(changes) == "review_wait"


def test_bottleneck_tie_goes_to_earlier_stage(vs, changes):
    pr = by_id(changes, "PR-101")
    tie = dict(pr, approved_at="2026-10-07T07:00:00+07:00", merged_at="2026-10-07T08:00:00+07:00", deployed_at="2026-10-07T09:00:00+07:00")
    assert vs.stage_durations(tie)["review"] == 20 * H
    assert vs.bottleneck([tie]) == "review_wait"


def test_flow_efficiency_is_aggregate(vs, changes):
    assert vs.flow_efficiency(changes) == pytest.approx(50 / 442.75)


def test_flow_efficiency_custom_active(vs, changes):
    assert vs.flow_efficiency(changes, active=("coding",)) == pytest.approx(37 / 442.75)


def test_empty(vs, changes):
    wip = [by_id(changes, "PR-108")]
    assert vs.stage_medians(wip) == {}
    assert vs.bottleneck(wip) is None
    assert vs.flow_efficiency(wip) is None
