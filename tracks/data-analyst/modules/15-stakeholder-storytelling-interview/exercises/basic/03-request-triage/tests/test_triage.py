import math
from pathlib import Path

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
COLUMNS = ["id", "requester", "ask", "decision", "impact", "effort_hours", "recurring", "in_dashboard"]


@pytest.fixture(scope="module")
def triage():
    return ex.module("triage.py")


def req(**kw):
    base = {"id": "X", "requester": "PM", "ask": "?", "decision": "Quyết định gì đó", "impact": 3,
            "effort_hours": 2.0, "recurring": False, "in_dashboard": False}
    base.update(kw)
    return base


def frame(rows):
    return pd.DataFrame([req(**r) for r in rows], columns=COLUMNS)


def load_backlog():
    src = Path(__file__).resolve().parents[1] / "starter" / "backlog.csv"
    return pd.read_csv(src)


@pytest.mark.parametrize("kw, route", [
    ({"in_dashboard": True, "decision": None}, "self-serve"),        # đã có số: gửi link, kể cả khi chưa rõ quyết định
    ({"in_dashboard": True, "recurring": True}, "self-serve"),
    ({"decision": None}, "clarify"),
    ({"decision": float("nan")}, "clarify"),                          # ô trống trong CSV đọc bằng pandas là NaN
    ({"decision": "   "}, "clarify"),
    ({"decision": None, "recurring": True, "effort_hours": 30}, "clarify"),
    ({"recurring": True, "effort_hours": 30}, "dashboard"),
    ({"effort_hours": 4.5}, "project"),
    ({"effort_hours": 4}, "ad-hoc"),                                  # đúng nửa ngày vẫn là ad-hoc
    ({"effort_hours": 0.5}, "ad-hoc"),
])
def test_classify(triage, kw, route):
    assert triage.classify(req(**kw)) == route


@pytest.mark.parametrize("impact, effort, quad", [
    (4, 8, "quick win"), (5, 1, "quick win"), (4, 8.5, "big bet"), (5, 40, "big bet"),
    (3, 8, "fill-in"), (1, 0.5, "fill-in"), (3, 9, "money pit"), (2, 40, "money pit"),
])
def test_quadrant(triage, impact, effort, quad):
    assert triage.quadrant(impact, effort) == quad


def test_prioritize_columns_and_no_mutation(triage):
    df = frame([{"id": "A"}, {"id": "B", "in_dashboard": True}])
    before = df.copy()
    out = triage.prioritize(df)
    pd.testing.assert_frame_equal(df, before)
    assert list(out.columns) == COLUMNS + ["route", "quadrant", "score"]
    assert list(out.index) == list(range(len(out)))


def test_prioritize_order(triage):
    df = frame([
        {"id": "F1", "impact": 3, "effort_hours": 1},                       # fill-in, score 3
        {"id": "Q1", "impact": 4, "effort_hours": 4},                       # quick win, 1.0
        {"id": "S1", "impact": 5, "effort_hours": 1, "in_dashboard": True},  # self-serve: cuối
        {"id": "B1", "impact": 5, "effort_hours": 10},                      # big bet, 0.5
        {"id": "Q2", "impact": 5, "effort_hours": 2},                       # quick win, 2.5
        {"id": "M1", "impact": 2, "effort_hours": 40},                      # money pit
        {"id": "C1", "decision": None, "impact": 5, "effort_hours": 1},     # clarify: cuối
        {"id": "B2", "impact": 4, "effort_hours": 10},                      # big bet, 0.4
        {"id": "Q3", "impact": 4, "effort_hours": 1.6},                     # quick win, 2.5 (hoà Q2, xếp theo id)
    ])
    out = triage.prioritize(df)
    assert out["id"].tolist() == ["Q2", "Q3", "Q1", "B1", "B2", "F1", "M1", "C1", "S1"]
    got = dict(zip(out["id"], out["score"]))
    assert got["Q1"] == pytest.approx(1.0) and got["B2"] == pytest.approx(0.4)
    assert dict(zip(out["id"], out["route"]))["S1"] == "self-serve"
    assert dict(zip(out["id"], out["quadrant"]))["M1"] == "money pit"


def test_plan_week_greedy_skips_what_does_not_fit(triage):
    df = frame([
        {"id": "Q1", "impact": 5, "effort_hours": 6},    # quick win
        {"id": "B1", "impact": 4, "effort_hours": 20},   # big bet, score 0.2: xếp sau B2
        {"id": "B2", "impact": 4, "effort_hours": 12},   # big bet, vừa
        {"id": "F1", "impact": 2, "effort_hours": 2},    # fill-in, vừa
        {"id": "M1", "impact": 1, "effort_hours": 1},    # fill-in (effort thấp), vừa
        {"id": "M2", "impact": 2, "effort_hours": 9},    # money pit: không bao giờ tự xếp lịch
        {"id": "S1", "in_dashboard": True, "effort_hours": 1},
        {"id": "C1", "decision": "", "effort_hours": 1},
    ])
    assert triage.plan_week(df, 20) == ["Q1", "B2", "F1"]
    assert triage.plan_week(df, 41) == ["Q1", "B2", "B1", "F1", "M1"]
    assert triage.plan_week(df, 0) == []


def test_backlog_routes(triage):
    out = triage.prioritize(load_backlog())
    routes = dict(zip(out["id"], out["route"]))
    assert routes["R02"] == "self-serve" and routes["R11"] == "self-serve"
    assert routes["R03"] == "clarify"
    assert routes["R04"] == "dashboard"
    assert routes["R07"] == "ad-hoc" and routes["R12"] == "ad-hoc"
    assert routes["R01"] == "project" and routes["R06"] == "project"
    assert out["id"].tolist() == ["R04", "R09", "R01", "R08", "R05", "R10", "R12", "R07", "R06", "R02", "R03", "R11"]


def test_backlog_week_plan(triage):
    assert triage.plan_week(load_backlog(), 30) == ["R04", "R09", "R01", "R08", "R12", "R07"]
    assert math.isclose(sum(load_backlog().set_index("id").loc[["R04", "R09", "R01", "R08", "R12", "R07"], "effort_hours"]), 26)
