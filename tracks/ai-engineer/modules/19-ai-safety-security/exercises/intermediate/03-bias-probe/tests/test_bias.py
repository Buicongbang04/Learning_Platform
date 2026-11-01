import itertools

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("bias.ipynb")


def test_probe_design(nb):
    assert len(nb.CVS) == 12 and {t for t, _ in nb.CVS} == {"mạnh", "vừa", "yếu"}
    text = nb.profile("Nguyễn Văn Hùng", "nam", "Hà Nội", nb.CVS[0][1])
    assert "Nguyễn Văn Hùng" in text and "Hà Nội" in text and nb.CVS[0][1] in text


@pytest.mark.parametrize("reply, expected", [
    ('{"score": 7}', 7), ('{"score": 1}', 1), ('{"score": 10}', 10), (' {"score": 3, "x": 1} ', 3),
    ('{"score": 0}', None), ('{"score": 11}', None), ('{"score": 7.0}', None), ('{"score": "7"}', None),
    ('{"score": true}', None), ('{"diem": 7}', None), ('điểm 7', None), ('[7]', None), ('{"score": null}', None),
])
def test_parse_score(nb, reply, expected):
    assert nb.parse_score(reply) == expected


def frame(score):
    rows = []
    for cv, g, ni, p in itertools.product(range(3), ["nam", "nữ"], [0, 1], ["HN", "CT"]):
        rows.append(dict(cv=cv, gender=g, name_idx=ni, province=p, score=score(cv, g, ni, p)))
    return pd.DataFrame(rows).sample(frac=1, random_state=0).reset_index(drop=True)


def test_paired_diffs(nb):
    df = frame(lambda cv, g, ni, p: 5 + cv + (1 if g == "nam" else 0) + (2 if (p == "CT" and cv == 2) else 0))
    out = nb.paired_diffs(df, "gender", "nam", "nữ", ["cv", "name_idx", "province"])
    assert list(out.columns) == ["cv", "name_idx", "province", "diff"]
    assert len(out) == 12 and (out["diff"] == 1).all()
    prov = nb.paired_diffs(df, "province", "CT", "HN", ["cv", "gender", "name_idx"])
    assert sorted(prov["diff"]) == [0] * 8 + [2] * 4
    assert (prov[prov.cv == 2]["diff"] == 2).all()


def test_paired_diffs_rejects_bad_keys(nb):
    df = frame(lambda *a: 5)
    with pytest.raises(ValueError):
        nb.paired_diffs(df, "gender", "nam", "nữ", ["cv", "province"])
    with pytest.raises(ValueError):
        nb.paired_diffs(df.drop(index=df.index[0]), "gender", "nam", "nữ", ["cv", "name_idx", "province"])


def test_flip_rate(nb):
    df = frame(lambda cv, g, ni, p: {0: 9, 1: 7, 2: 3}[cv] - (1 if (g == "nữ" and ni == 0) else 0))
    assert nb.flip_rate(df, "gender", "nam", "nữ", ["cv", "name_idx", "province"], 7) == pytest.approx(2 / 12)
    assert nb.flip_rate(df, "gender", "nam", "nữ", ["cv", "name_idx", "province"], 9) == pytest.approx(2 / 12)
    assert nb.flip_rate(df, "gender", "nam", "nữ", ["cv", "name_idx", "province"], 5) == 0.0


def test_cluster_bootstrap(nb):
    values = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    clusters = np.array([0, 0, 0, 1, 1, 1])
    mean, lo, hi = nb.cluster_bootstrap_ci(values, clusters, n_boot=4000, seed=0)
    assert mean == pytest.approx(0.5)
    assert lo == pytest.approx(0.0) and hi == pytest.approx(1.0), "chỉ 2 cụm: mỗi vòng chỉ ra 0, 0.5 hoặc 1"
    independent = np.arange(6)
    _, lo2, hi2 = nb.cluster_bootstrap_ci(values, independent, n_boot=4000, seed=0)
    assert hi2 - lo2 < hi - lo, "coi từng cặp độc lập cho khoảng hẹp hơn (hẹp giả)"
    rng = np.random.default_rng(1)
    v = rng.normal(0.3, 1.0, 400)
    c = np.repeat(np.arange(40), 10)
    m, lo, hi = nb.cluster_bootstrap_ci(v, c, seed=3)
    assert lo < m < hi and m == pytest.approx(v.mean())
    assert nb.cluster_bootstrap_ci(v, c, seed=3) == (m, lo, hi), "cùng seed, cùng kết quả"


def test_cluster_bootstrap_exact_draws(nb):
    values = np.array([4.0, 2.0, 0.0, 4.0, 6.0])
    clusters = np.array(["b", "a", "c", "b", "b"])
    _, lo, hi = nb.cluster_bootstrap_ci(values, clusters, n_boot=5, seed=7)
    rng = np.random.default_rng(7)
    groups = [np.array([2.0]), np.array([4.0, 4.0, 6.0]), np.array([0.0])]
    means = [np.concatenate([groups[j] for j in rng.integers(0, 3, 3)]).mean() for _ in range(5)]
    assert (lo, hi) == (pytest.approx(np.quantile(means, 0.025)), pytest.approx(np.quantile(means, 0.975)))


def test_weat_effect_size_hand_example(nb):
    X = np.array([[1.0, 0.0], [2.0, 0.2]])
    Y = np.array([[0.0, 1.0], [0.1, 3.0]])
    A = np.array([[1.0, 0.0]])
    B = np.array([[0.0, 1.0]])
    unit = lambda M: M / np.linalg.norm(M, axis=1, keepdims=True)
    s = [float(unit(w[None])[0] @ unit(A)[0] - unit(w[None])[0] @ unit(B)[0]) for w in [*X, *Y]]
    expected = (np.mean(s[:2]) - np.mean(s[2:])) / np.std(s, ddof=1)
    assert nb.weat_effect_size(X, Y, A, B) == pytest.approx(expected)
    assert nb.weat_effect_size(Y, X, A, B) == pytest.approx(-expected)
    assert nb.weat_effect_size(X * 5, Y, A * 0.1, B * 7) == pytest.approx(expected), "phải chuẩn hoá L2"


def test_weat_p_value(nb):
    rng = np.random.default_rng(0)
    A = rng.normal(size=(8, 16)) + np.eye(16)[0] * 4
    B = rng.normal(size=(8, 16)) + np.eye(16)[1] * 4
    X = rng.normal(size=(6, 16)) + np.eye(16)[0] * 3
    Y = rng.normal(size=(6, 16)) + np.eye(16)[1] * 3
    p = nb.weat_p_value(X, Y, A, B, n_perm=2000, seed=0)
    assert p < 0.01
    assert nb.weat_p_value(Y, X, A, B, n_perm=2000, seed=0) > 0.99, "một phía"
    assert nb.weat_p_value(X, Y, A, B, n_perm=99, seed=0) >= 1 / 100
    Z = rng.normal(size=(12, 16))
    p_null = nb.weat_p_value(Z[:6], Z[6:], A, B, n_perm=2000, seed=0)
    assert 0.02 < p_null < 0.98
