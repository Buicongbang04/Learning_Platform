import math
import re

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("online.ipynb")


class Scripted:
    """RNG giả trả lần lượt các giá trị cho trước, ghi số lần bị gọi."""

    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    def random(self):
        self.calls += 1
        return self.values.pop(0)


# ---------- team-draft interleaving ----------

def test_interleave_scripted_coin(nb):
    a = ["a1", "a2", "a3", "x"]
    b = ["b1", "x", "b2", "a1"]
    rng = Scripted([0.2, 0.9, 0.3])
    merged, team = nb.team_draft_interleave(a, b, 6, rng)
    assert merged == ["a1", "b1", "x", "a2", "a3", "b2"]
    assert team == {"a1": "A", "b1": "B", "x": "B", "a2": "A", "a3": "A", "b2": "B"}
    assert rng.calls == 3, "chỉ tung đồng xu khi hai đội bằng số phần tử"


def test_interleave_identical_lists_and_exhaustion(nb):
    rng = np.random.default_rng(0)
    merged, team = nb.team_draft_interleave(list("pqrst"), list("pqrst"), 5, rng)
    assert merged == list("pqrst"), "hai danh sách giống nhau thì danh sách trộn giữ nguyên thứ tự"
    merged, team = nb.team_draft_interleave(["a"], ["b", "c", "d"], 10, Scripted([0.1, 0.1]))
    assert merged == ["a", "b", "c", "d"] and team == {"a": "A", "b": "B", "c": "B", "d": "B"}, \
        "đội hết phần tử mới thì đội kia chọn"


def test_interleave_properties_random(nb):
    rng = np.random.default_rng(1)
    first_a = 0
    for trial in range(400):
        pool = [f"d{i}" for i in range(15)]
        a = list(rng.permutation(pool)[:10])
        b = list(rng.permutation(pool)[:10])
        merged, team = nb.team_draft_interleave(a, b, 10, rng)
        assert len(merged) == len(set(merged)) == 10 and set(team) == set(merged)
        counts = [sum(v == t for v in team.values()) for t in "AB"]
        assert abs(counts[0] - counts[1]) <= 1
        for side, src in (("A", a), ("B", b)):
            picked = [d for d in merged if team[d] == side]
            assert picked == [d for d in src if d in picked], "mỗi đội lấy theo đúng thứ tự xếp hạng của mình"
        for i, d in enumerate(merged):
            src = a if team[d] == "A" else b
            assert d == next(x for x in src if x not in merged[:i]), "luôn lấy phần tử cao nhất chưa có"
        first_a += team[merged[0]] == "A"
    assert 0.42 <= first_a / 400 <= 0.58


def test_interleave_outcome(nb):
    team = {"a": "A", "b": "B", "c": "A"}
    assert nb.interleave_outcome(["a", "c", "b"], team) == "A"
    assert nb.interleave_outcome(["b"], team) == "B"
    assert nb.interleave_outcome(["a", "b"], team) == "tie"
    assert nb.interleave_outcome([], team) == "tie"
    assert nb.interleave_outcome(["zzz", "b"], team) == "B"


# ---------- click model ----------

def test_cascade_clicks_scripted(nb):
    rng = Scripted([0.05, 0.95, 0.5, 0.3, 0.1])
    clicks = nb.cascade_clicks(["n1", "r1", "n2", "r2", "n3"], {"r1", "r2"}, rng)
    assert clicks == ["n1", "r2"]
    assert rng.calls == 5, "click liên quan mới tung thêm một lần để quyết định dừng"
    rng = Scripted([0.5, 0.2, 0.7])
    assert nb.cascade_clicks(["r1", "n1", "r2"], {"r1", "r2"}, rng) == ["r1"] and rng.calls == 2


def test_cascade_clicks_rates(nb):
    rng = np.random.default_rng(0)
    first_rel = sum("r" in nb.cascade_clicks(["r", "n"], {"r"}, rng) for _ in range(20_000)) / 20_000
    assert first_rel == pytest.approx(0.9, abs=0.01)
    n_clicks = [len(nb.cascade_clicks(["n1", "n2", "n3"], set(), rng)) for _ in range(20_000)]
    assert np.mean(n_clicks) == pytest.approx(0.3, abs=0.02)


# ---------- thống kê ----------

def test_ab_sample_size(nb):
    assert nb.ab_sample_size(0.8, 0.75) == 1094
    assert nb.ab_sample_size(0.5, 0.6) == 388
    assert nb.ab_sample_size(0.6, 0.5) == 388
    assert nb.ab_sample_size(0.8, 0.75, power=0.9) > 1094
    small, big = nb.ab_sample_size(0.5, 0.52), nb.ab_sample_size(0.5, 0.54)
    assert 3.6 <= small / big <= 4.2, "chênh lệch giảm một nửa thì cần khoảng gấp bốn số mẫu"
    for bad in [(0.5, 0.5), (0.0, 0.5), (0.5, 1.0)]:
        with pytest.raises(ValueError):
            nb.ab_sample_size(*bad)


def test_sign_test_matches_scipy(nb):
    from scipy.stats import binomtest

    for wa, wb in [(10, 2), (7, 7), (30, 18), (0, 5), (100, 70)]:
        assert nb.sign_test_pvalue(wa, wb) == pytest.approx(binomtest(wa, wa + wb, 0.5).pvalue)
    assert nb.sign_test_pvalue(0, 0) == 1.0


def test_psi(nb):
    edges = [0, 1, 2, 3]
    e = [0.5] * 50 + [1.5] * 30 + [2.5] * 20
    a = [0.5] * 20 + [1.5] * 30 + [2.5] * 50
    expected = (0.2 - 0.5) * math.log(0.2 / 0.5) + 0 + (0.5 - 0.2) * math.log(0.5 / 0.2)
    assert nb.psi(e, a, edges) == pytest.approx(expected)
    assert nb.psi(e, e, edges) == pytest.approx(0.0)
    empty_bin = nb.psi([0.5] * 10, [0.5] * 5 + [2.5] * 5, edges)
    assert math.isfinite(empty_bin) and empty_bin > 1.0, "bin rỗng được kẹp ở 1e-4, không ra vô cùng"


# ---------- báo cáo ----------

def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 500, "báo cáo: ít nhất 500 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng"
