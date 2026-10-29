import numpy as np
import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)

# Ví dụ trong phần 7 lý thuyết module 00 (Olist dashboard hằng ngày)
W = {"latency": 0.25, "ops_cost": 0.25, "scalability": 0.15, "team_fit": 0.20, "observability": 0.15}
S = {"A": {"latency": 5, "ops_cost": 5, "scalability": 3, "team_fit": 5, "observability": 2},
     "B": {"latency": 5, "ops_cost": 4, "scalability": 4, "team_fit": 4, "observability": 5},
     "C": {"latency": 5, "ops_cost": 1, "scalability": 5, "team_fit": 1, "observability": 4}}


@pytest.fixture(scope="module")
def dm():
    return ex.module("decision_matrix.py")


@pytest.fixture(scope="module")
def matrix():
    return yaml.safe_load(ex.read("matrix.yaml"))


# ---------- ma trận có trọng số ----------

def test_weighted_scores_match_theory_example(dm):
    got = dm.weighted_scores(S, W)
    assert got == {"A": pytest.approx(4.25), "B": pytest.approx(4.40), "C": pytest.approx(3.05)}


def test_rank(dm):
    assert [name for name, _ in dm.rank(S, W)] == ["B", "A", "C"]


@pytest.mark.parametrize("bad", [
    ({**W, "latency": 0.30}, S),                                       # tổng 1,05
    ({**W, "latency": -0.05, "ops_cost": 0.55}, S),                     # trọng số âm
    (W, {**S, "A": {**S["A"], "latency": 6}}),                         # điểm ngoài 1..5
    (W, {**S, "B": {k: v for k, v in S["B"].items() if k != "team_fit"}}),   # thiếu tiêu chí
])
def test_validate_rejects(dm, bad):
    weights, scores = bad
    with pytest.raises(ValueError):
        dm.weighted_scores(scores, weights)


def test_reweight_keeps_proportions(dm):
    w = dm.reweight(W, "scalability", 0.5)
    assert w["scalability"] == pytest.approx(0.5)
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["latency"] / w["team_fit"] == pytest.approx(0.25 / 0.20)
    assert W["scalability"] == 0.15                                    # không sửa dict gốc


# Biến thể không có hoà điểm chính xác (ví dụ lý thuyết có A và B bằng nhau khi bỏ hẳn một tiêu chí,
# điểm đổi nằm đúng ở mép 0 và phụ thuộc sai số dấu phẩy động)
S2 = {"A": {"latency": 5, "ops_cost": 5, "scalability": 3, "team_fit": 5, "observability": 2},
      "B": {"latency": 4, "ops_cost": 4, "scalability": 4, "team_fit": 4, "observability": 5},
      "C": {"latency": 5, "ops_cost": 1, "scalability": 5, "team_fit": 2, "observability": 4}}


def _winner(weights):
    totals = {o: sum(weights[c] * s[c] for c in weights) for o, s in S2.items()}
    return max(sorted(totals), key=lambda o: totals[o])


def _brute_flip(criterion):
    w0, base = W[criterion], _winner(W)
    others = 1 - w0
    best = None
    for w in np.linspace(0, 1, 10_001):
        weights = {c: (w if c == criterion else W[c] * (1 - w) / others) for c in W}
        if _winner(weights) != base and (best is None or abs(w - w0) < abs(best - w0)):
            best = w
    return best


@pytest.mark.parametrize("criterion", list(W))
def test_flip_point_matches_brute_force(dm, criterion):
    expected = _brute_flip(criterion)
    got = dm.flip_point(S2, W, criterion)
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected, abs=2e-3)


# ---------- ma trận của bạn ----------

def test_matrix_is_filled(matrix):
    text = ex.read("matrix.yaml")
    assert "TODO" not in text, "Điền hết TODO trong matrix.yaml"
    assert len(matrix["options"]) >= 3
    assert len(matrix["weights"]) >= 5


def test_matrix_is_valid_and_decision_consistent(dm, matrix):
    ranking = dm.rank(matrix["scores"], matrix["weights"])      # validate bên trong
    assert set(matrix["scores"]) == set(matrix["options"])
    assert matrix["decision"] in matrix["options"]
    if matrix["decision"] != ranking[0][0]:
        assert matrix.get("override_reason"), "Chọn khác phương án điểm cao nhất thì phải ghi override_reason"


def test_volume_estimate_from_real_data(matrix):
    v = matrix["volume_estimate"]
    assert 50 <= v["bytes_per_reading"] <= 200, "Dùng byte mỗi dòng CSV thô đo được trên bộ UCI (~84)"
    assert v["readings_per_station_per_day"] >= 24
    expected = v["stations"] * v["readings_per_station_per_day"] * v["bytes_per_reading"] * 365 / 1e9
    assert v["raw_gb_per_year"] == pytest.approx(expected, rel=0.1)


def test_decision_document():
    text = ex.read("decision.md")
    assert "TODO" not in text, "Điền hết TODO trong decision.md"
    for heading in ("## Bài toán", "## Ước lượng khối lượng", "## Phương án", "## Tiêu chí và trọng số",
                    "## Ma trận", "## Độ nhạy", "## Quyết định"):
        assert heading in text
