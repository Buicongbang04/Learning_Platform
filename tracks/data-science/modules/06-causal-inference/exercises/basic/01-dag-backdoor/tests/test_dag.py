import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from testkit import Exercise

ex = Exercise(__file__)

CONFOUNDER = [("Z", "T"), ("Z", "Y"), ("T", "Y")]
COLLIDER = [("T", "Y"), ("T", "C"), ("Y", "C")]
MEDIATOR = [("T", "M"), ("M", "Y")]
M_BIAS = [("A", "T"), ("A", "M"), ("B", "M"), ("B", "Y"), ("T", "Y")]
# Olist thu gọn: vùng xa và mùa cao điểm gây cả giao trễ lẫn review xấu; liên hệ CSKH là mediator
OLIST = [
    ("region", "late"), ("region", "bad_review"), ("season", "late"), ("season", "bad_review"),
    ("late", "contact_cs"), ("contact_cs", "bad_review"), ("late", "bad_review"),
]


@pytest.fixture(scope="module")
def dag():
    return ex.module("dag.py")


def test_descendants(dag):
    assert dag.descendants(OLIST, "late") == {"contact_cs", "bad_review"}
    assert dag.descendants(M_BIAS, "A") == {"T", "M", "Y"}
    assert dag.descendants(MEDIATOR, "Y") == set()


@pytest.mark.parametrize("edges, z, expected", [
    ([("X", "M"), ("M", "Y")], set(), False),          # chain: mở
    ([("X", "M"), ("M", "Y")], {"M"}, True),           # chain: chặn khi điều kiện trên M
    ([("M", "X"), ("M", "Y")], set(), False),          # fork: mở
    ([("M", "X"), ("M", "Y")], {"M"}, True),           # fork: chặn
    ([("X", "C"), ("Y", "C")], set(), True),           # collider: tự chặn
    ([("X", "C"), ("Y", "C")], {"C"}, False),          # điều kiện trên collider: mở
    ([("X", "C"), ("Y", "C"), ("C", "D")], {"D"}, False),  # điều kiện trên hậu duệ collider: cũng mở
])
def test_d_separated_three_building_blocks(dag, edges, z, expected):
    assert dag.d_separated(edges, "X", "Y", z) is expected


def test_d_separated_longer_path(dag):
    edges = [("A", "B"), ("B", "C"), ("D", "C"), ("D", "E")]
    assert dag.d_separated(edges, "A", "E", set())
    assert not dag.d_separated(edges, "A", "E", {"C"})
    assert dag.d_separated(edges, "A", "E", {"C", "D"})


@pytest.mark.parametrize("edges, t, y, z, expected", [
    (CONFOUNDER, "T", "Y", set(), False),
    (CONFOUNDER, "T", "Y", {"Z"}, True),
    (COLLIDER, "T", "Y", set(), True),
    (COLLIDER, "T", "Y", {"C"}, False),      # C là hậu duệ của T
    (MEDIATOR, "T", "Y", set(), True),
    (MEDIATOR, "T", "Y", {"M"}, False),      # điều kiện trên mediator cắt mất một phần tác động
    (M_BIAS, "T", "Y", set(), True),
    (M_BIAS, "T", "Y", {"M"}, False),        # M-bias: M là collider giữa A và B
    (M_BIAS, "T", "Y", {"M", "A"}, True),
    (M_BIAS, "T", "Y", {"M", "B"}, True),
    (OLIST, "late", "bad_review", {"region", "season"}, True),
    (OLIST, "late", "bad_review", {"region"}, False),
    (OLIST, "late", "bad_review", {"region", "season", "contact_cs"}, False),
])
def test_backdoor_criterion(dag, edges, t, y, z, expected):
    assert dag.satisfies_backdoor(edges, t, y, z) is expected


def simulate(kind: str, n: int = 20000, seed: int = 0) -> pd.DataFrame:
    """Tác động thật của T lên Y là 2.0 trong mọi kịch bản."""
    rng = np.random.default_rng(seed)
    if kind == "confounder":
        z = rng.normal(size=n)
        t = 1.5 * z + rng.normal(size=n)
        y = 2.0 * t + 3.0 * z + rng.normal(size=n)
        return pd.DataFrame({"Z": z, "T": t, "Y": y})
    t = rng.normal(size=n)
    y = 2.0 * t + rng.normal(size=n)
    c = t + y + rng.normal(size=n)
    return pd.DataFrame({"T": t, "Y": y, "C": c})


def test_ols_effect_matches_statsmodels(dag):
    df = simulate("confounder", n=500, seed=1)
    ref = sm.OLS(df.Y, sm.add_constant(df[["T", "Z"]])).fit().params["T"]
    assert dag.ols_effect(df, "T", "Y", ["Z"]) == pytest.approx(ref, abs=1e-8)
    ref0 = sm.OLS(df.Y, sm.add_constant(df[["T"]])).fit().params["T"]
    assert dag.ols_effect(df, "T", "Y", []) == pytest.approx(ref0, abs=1e-8)


@pytest.mark.parametrize("seed", range(5))
def test_adjusting_confounder_removes_bias(dag, seed):
    df = simulate("confounder", seed=seed)
    assert dag.ols_effect(df, "T", "Y", []) > 3.0              # lệch lên rất xa 2.0
    assert dag.ols_effect(df, "T", "Y", ["Z"]) == pytest.approx(2.0, abs=0.05)


@pytest.mark.parametrize("seed", range(5))
def test_adjusting_collider_creates_bias(dag, seed):
    df = simulate("collider", seed=seed)
    assert dag.ols_effect(df, "T", "Y", []) == pytest.approx(2.0, abs=0.05)
    assert abs(dag.ols_effect(df, "T", "Y", ["C"]) - 2.0) > 0.5
