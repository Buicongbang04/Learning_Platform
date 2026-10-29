import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)

BASE = {"flagged_per_week": 70, "precision": 0.391, "effect": 0.15, "loss_event": 30.0, "cost_action": 0.5}
RANGES = {"effect": (0.05, 0.25), "loss_event": (5.0, 60.0), "precision": (0.33, 0.45),
          "cost_action": (0.2, 1.0), "flagged_per_week": (50, 140)}


@pytest.fixture(scope="module")
def sizing():
    return ex.module("sizing.py")


def toy(a, b, c):
    return a * b - c


def test_weekly_value(sizing):
    assert sizing.weekly_value(70, 0.391, 0.15, 30, 0.5) == pytest.approx(70 * (0.391 * 4.5 - 0.5))
    assert sizing.weekly_value(100, 1.0, 0.15, 30, 5.0) < 0


def test_tornado_toy(sizing):
    out = sizing.tornado(toy, {"a": 2, "b": 3, "c": 1}, {"a": (1, 5), "b": (2, 3), "c": (0, 10)})
    assert list(out.param) == ["a", "c", "b"]
    assert list(out.index) == [0, 1, 2]
    row = out.set_index("param").loc["c"]
    assert row.value_low == pytest.approx(6) and row.value_high == pytest.approx(-4) and row.swing == pytest.approx(10)
    assert out.set_index("param").loc["a", "swing"] == pytest.approx(12)


def test_tornado_on_memo_assumptions(sizing):
    out = sizing.tornado(sizing.weekly_value, BASE, RANGES)
    assert set(out.param) == set(RANGES)
    assert out.swing.is_monotonic_decreasing
    assert out.param.iloc[0] == "loss_event"


def test_scenarios(sizing):
    s = sizing.scenarios(toy, {"a": 2, "b": 3, "c": 1}, {"a": (1, 5), "c": (0, 10)})
    assert s["base"] == pytest.approx(5)
    assert s["pessimistic"] == pytest.approx(1 * 3 - 10)
    assert s["optimistic"] == pytest.approx(5 * 3 - 0)
    real = sizing.scenarios(sizing.weekly_value, BASE, RANGES)
    assert real["pessimistic"] < 0 < real["base"] < real["optimistic"]


def test_break_even(sizing):
    v = sizing.break_even(sizing.weekly_value, BASE, "loss_event", 0.1, 100)
    assert v == pytest.approx(0.5 / (0.391 * 0.15), rel=1e-6)
    assert sizing.break_even(toy, {"a": 2, "b": 3, "c": 1}, "c", 0, 100) == pytest.approx(6)
    with pytest.raises(ValueError):
        sizing.break_even(sizing.weekly_value, BASE, "loss_event", 20, 100)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo
    words = len(memo.split())
    assert 250 <= words <= 700, f"Memo có {words} từ: một trang là 250–700 từ"
    headings = re.findall(r"^## (.+)$", memo, re.M)
    assert headings and headings[0].strip() == "Khuyến nghị"
    assert "R$" in memo and re.search(r"\d", memo)
