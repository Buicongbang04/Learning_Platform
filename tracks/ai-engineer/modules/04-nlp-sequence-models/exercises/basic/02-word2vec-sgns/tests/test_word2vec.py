import numpy as np
import pytest
import torch
import torch.nn.functional as F
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def w2v():
    return ex.module("word2vec.py")


def test_build_vocab_order_and_min_count(w2v):
    tokens = "e a c a e a d b b".split()
    word2id, counts = w2v.build_vocab(tokens, min_count=2)
    assert word2id == {"a": 0, "b": 1, "e": 2}, "tần suất giảm dần, hoà thì theo thứ tự chữ cái; bỏ từ < min_count"
    assert counts.tolist() == [3, 2, 2] and counts.dtype == np.int64


def test_keep_probs(w2v):
    counts = np.array([5000, 300, 100, 1], dtype=np.int64)    # tổng 5401
    p = w2v.keep_probs(counts, t=1e-3)
    assert p[0] == pytest.approx(0.033947, abs=1e-6)
    assert p[1] == pytest.approx(0.152180, abs=1e-6)
    assert p[2] == pytest.approx(0.286411, abs=1e-6)
    assert p[3] == 1.0, "từ hiếm luôn được giữ (xác suất cắt ở 1)"
    assert np.all(np.diff(p) >= 0)


def test_noise_distribution(w2v):
    counts = np.array([16, 1], dtype=np.int64)
    p = w2v.noise_distribution(counts)
    assert p.sum() == pytest.approx(1.0)
    assert p[0] / p[1] == pytest.approx(8.0), "16^0.75 / 1^0.75 = 8: mũ 0.75 nâng từ hiếm lên"
    assert w2v.noise_distribution(counts, power=1.0)[1] == pytest.approx(1 / 17)


def test_skipgram_pairs(w2v):
    pairs = w2v.skipgram_pairs(np.array([10, 11, 12, 13]), window=1)
    assert pairs.tolist() == [[10, 11], [11, 10], [11, 12], [12, 11], [12, 13], [13, 12]]
    pairs2 = w2v.skipgram_pairs(np.array([1, 2, 3]), window=5)
    assert pairs2.shape == (6, 2) and pairs2.dtype == np.int64
    assert w2v.skipgram_pairs(np.array([7]), window=2).shape == (0, 2)


def torch_reference(W_in, W_out, c, o, neg):
    Wi = torch.tensor(W_in, requires_grad=True)
    Wo = torch.tensor(W_out, requires_grad=True)
    v = Wi[torch.tensor(c)]
    s_pos = (v * Wo[torch.tensor(o)]).sum(1)
    s_neg = torch.einsum("bkd,bd->bk", Wo[torch.tensor(neg)], v)
    loss = -(F.logsigmoid(s_pos).sum() + F.logsigmoid(-s_neg).sum()) / len(c)
    loss.backward()
    return loss.item(), Wi.grad.numpy(), Wo.grad.numpy()


def test_sgns_step_matches_torch_with_repeated_ids(w2v):
    rng = np.random.default_rng(0)
    V, D = 7, 5
    W_in = rng.normal(0, 0.5, (V, D))
    W_out = rng.normal(0, 0.5, (V, D))
    c = np.array([0, 0, 3, 5])              # center lặp lại
    o = np.array([1, 2, 1, 1])              # context lặp lại
    neg = np.array([[4, 6, 4], [1, 6, 2], [0, 0, 6], [3, 1, 2]])  # negative trùng nhau và trùng context
    ref_loss, gi, go = torch_reference(W_in, W_out, c, o, neg)
    lr = 0.1
    exp_in, exp_out = W_in - lr * gi, W_out - lr * go
    loss = w2v.sgns_step(W_in, W_out, c, o, neg, lr)
    assert isinstance(loss, float)
    assert loss == pytest.approx(ref_loss, rel=1e-10)
    np.testing.assert_allclose(W_in, exp_in, atol=1e-12,
                               err_msg="W_in sai: chỉ số lặp phải cộng dồn (np.add.at), không gán đè")
    np.testing.assert_allclose(W_out, exp_out, atol=1e-12)


def test_sgns_stable_for_large_scores(w2v):
    W_in = np.full((3, 2), 30.0)
    W_out = np.full((3, 2), -30.0)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        loss = w2v.sgns_step(W_in, W_out, np.array([0]), np.array([1]), np.array([[2]]), 0.0)
    assert np.isfinite(loss) and loss == pytest.approx(1800.0, rel=1e-6)


def test_most_similar(w2v):
    W = np.array([[1.0, 0.0], [10.0, 1.0], [0.0, 1.0], [-1.0, 0.0]])
    word2id = {"a": 0, "b": 1, "c": 2, "d": 3}
    out = w2v.most_similar(W, word2id, "a", 2)
    assert [w for w, _ in out] == ["b", "c"], "cosine, không phải tích vô hướng; bỏ chính từ đó"
    assert out[0][1] == pytest.approx(10 / np.sqrt(101))


def test_training_learns_topics(w2v):
    # Hai chủ đề không bao giờ chung câu: từ cùng chủ đề phải gần nhau hơn khác chủ đề.
    rng = np.random.default_rng(0)
    food = "phở bún cơm bánh chè xôi".split()
    sport = "bóng đá chạy bơi vợt cờ".split()
    sentences = [list(rng.choice(food if rng.random() < 0.5 else sport, 8)) for _ in range(400)]
    word2id, counts = w2v.build_vocab([w for s in sentences for w in s], 1)
    pairs = np.concatenate([w2v.skipgram_pairs(np.array([word2id[w] for w in s]), 2) for s in sentences])
    noise = w2v.noise_distribution(counts)
    W_in = rng.uniform(-0.5, 0.5, (len(word2id), 16)) / 16
    W_out = np.zeros((len(word2id), 16))
    losses = []
    for epoch in range(3):
        order = rng.permutation(len(pairs))
        for start in range(0, len(pairs), 64):
            b = pairs[order[start:start + 64]]
            neg = rng.choice(len(word2id), size=(len(b), 5), p=noise)
            losses.append(w2v.sgns_step(W_in, W_out, b[:, 0], b[:, 1], neg, 0.5))
    assert np.mean(losses[-50:]) < np.mean(losses[:50])
    top = [w for w, _ in w2v.most_similar(W_in, word2id, "phở", 5)]
    assert set(top) == set(food) - {"phở"}, f"5 từ gần 'phở' nhất phải là món ăn, được {top}"
