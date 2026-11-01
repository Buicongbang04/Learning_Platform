import numpy as np
import pytest
import torch
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def pr():
    return ex.module("probe.py")


def test_group_split_no_leak_and_reproducible(pr):
    groups = np.repeat(np.array([7, 3, 9, 1, 5, 2, 8, 4, 6, 0]), [3, 1, 4, 2, 5, 2, 3, 1, 2, 4])
    tr, te = pr.group_split(groups, 0.3, 0)
    assert set(groups[tr]).isdisjoint(groups[te]), "một nhóm chỉ nằm ở một phía"
    assert sorted(np.r_[tr, te].tolist()) == list(range(len(groups)))
    assert list(tr) == sorted(tr) and list(te) == sorted(te)
    assert len(set(groups[te])) == 3
    uniq = np.unique(groups)
    expected = uniq[np.random.default_rng(0).permutation(len(uniq))[:3]]
    assert set(groups[te]) == set(expected.tolist()), "np.unique rồi default_rng(seed).permutation, nhóm đầu vào test"
    tr2, te2 = pr.group_split(groups, 0.3, 0)
    assert np.array_equal(te, te2)
    assert not np.array_equal(te, pr.group_split(groups, 0.3, 1)[1])


def test_standardize_uses_train_statistics_only(pr):
    rng = np.random.default_rng(0)
    Xtr = rng.normal(2.0, 3.0, (200, 4))
    Xte = rng.normal(5.0, 1.0, (50, 4))
    a, b = pr.standardize(Xtr, Xte)
    np.testing.assert_allclose(a.mean(0), 0, atol=1e-6)
    np.testing.assert_allclose(a.std(0), 1, atol=1e-3)
    np.testing.assert_allclose(b, (Xte - Xtr.mean(0)) / (Xtr.std(0) + 1e-6), rtol=1e-5,
                               err_msg="mean và std chỉ lấy từ train")


def test_probe_matches_regularized_logistic_regression(pr):
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(1)
    X = rng.normal(size=(300, 5)).astype(np.float32)
    y = (X @ np.array([1.0, -2.0, 0.5, 0.0, 1.5]) + rng.normal(0, 1.0, 300) > 0).astype(int)
    y[X[:, 3] > 1.2] = 2
    wd = 0.01
    probe = pr.train_linear_probe(X, y, 3, weight_decay=wd, steps=500, seed=0)
    assert isinstance(probe, torch.nn.Linear) and probe.weight.shape == (3, 5)
    ref = LogisticRegression(C=1 / (2 * wd * len(X)), tol=1e-10, max_iter=10_000).fit(X, y)
    with torch.no_grad():
        p = torch.softmax(probe(torch.as_tensor(X)), -1).numpy()
    np.testing.assert_allclose(p, ref.predict_proba(X), atol=2e-3,
                               err_msg="loss = CE trung bình + weight_decay * ||W||^2, không phạt bias")


def test_probe_weight_decay_shrinks_and_seed_reproducible(pr):
    rng = np.random.default_rng(2)
    X = rng.normal(size=(200, 6)).astype(np.float32)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    small = pr.train_linear_probe(X, y, 2, weight_decay=1e-4, seed=0)
    big = pr.train_linear_probe(X, y, 2, weight_decay=1e-1, seed=0)
    assert big.weight.norm() < 0.5 * small.weight.norm()
    again = pr.train_linear_probe(X, y, 2, weight_decay=1e-4, seed=0)
    torch.testing.assert_close(small.weight, again.weight)
    assert pr.probe_accuracy(small, X, y) > 0.97
    assert isinstance(pr.probe_accuracy(small, X, y), float)


def test_control_labels(pr):
    rng = np.random.default_rng(3)
    tokens = rng.integers(0, 400, 5000)
    labels = (rng.random(5000) < 0.3).astype(int)
    ctrl = pr.control_labels(tokens, labels, 0)
    assert ctrl.shape == tokens.shape
    for t in np.unique(tokens)[:50]:
        assert len(set(ctrl[tokens == t])) == 1, "mỗi loại token một nhãn cố định"
    types = np.unique(tokens)
    per_type = np.array([ctrl[tokens == t][0] for t in types])
    values, counts = np.unique(labels, return_counts=True)
    expected = np.random.default_rng(0).choice(values, size=len(types), p=counts / counts.sum())
    assert np.array_equal(per_type, expected), "loại token sắp tăng, rút bằng default_rng(seed).choice theo phân phối nhãn"
    assert not np.array_equal(ctrl, pr.control_labels(tokens, labels, 1))


def test_group_split_blocks_memorization_leak(pr):
    rng = np.random.default_rng(4)
    n_groups, per = 60, 20
    groups = np.repeat(np.arange(n_groups), per)
    group_vec = rng.normal(size=(n_groups, 64)) * 3
    group_label = rng.integers(0, 2, n_groups)
    X = (group_vec[groups] + rng.normal(size=(n_groups * per, 64))).astype(np.float32)
    y = group_label[groups]
    tr, te = pr.group_split(groups, 0.3, 0)
    a, b = pr.standardize(X[tr], X[te])
    probe = pr.train_linear_probe(a, y[tr], 2, weight_decay=1e-3, seed=0)
    assert pr.probe_accuracy(probe, a, y[tr]) > 0.9
    assert pr.probe_accuracy(probe, b, y[te]) < 0.75, "nhãn chỉ gắn với nhóm: chia theo nhóm thì probe không đoán được"


def test_majority_baseline(pr):
    assert pr.majority_baseline(np.array([0, 1, 1, 2]), np.array([1, 1, 0, 2])) == 0.5
    assert pr.majority_baseline(np.array([2, 0, 2, 0]), np.array([0, 0, 2])) == pytest.approx(2 / 3)


def test_mean_difference_direction(pr):
    rng = np.random.default_rng(5)
    y = rng.integers(0, 2, 400)
    X = rng.normal(size=(400, 3)) + np.outer(y, [3.0, 0.0, -4.0])
    d = pr.mean_difference_direction(X, y)
    assert d.shape == (3,) and np.isclose(np.linalg.norm(d), 1.0)
    ref = X[y == 1].mean(0) - X[y == 0].mean(0)
    np.testing.assert_allclose(d, ref / np.linalg.norm(ref), rtol=1e-6)
