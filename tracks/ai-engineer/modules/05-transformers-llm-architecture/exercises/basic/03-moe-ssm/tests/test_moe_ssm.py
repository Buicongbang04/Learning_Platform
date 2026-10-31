import math

import pytest
import torch
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def M():
    return ex.module("moe_ssm.py")


def make_moe(M, n_experts=4, top_k=2, dim=6, seed=0):
    torch.manual_seed(seed)
    return M.MoE(dim, 12, n_experts, top_k)


def test_route_topk_and_weights(M):
    moe = make_moe(M)
    x = torch.randn(10, 6)
    top_idx, weights, probs = moe.route(x)
    logits = moe.gate(x)
    assert top_idx.shape == (10, 2) and weights.shape == (10, 2) and probs.shape == (10, 4)
    assert torch.equal(top_idx, logits.topk(2, dim=-1).indices)
    torch.testing.assert_close(weights, torch.softmax(logits.topk(2, dim=-1).values, dim=-1),
                               msg="trọng số: softmax trên k logits được chọn (kiểu Mixtral)")
    torch.testing.assert_close(probs, torch.softmax(logits, dim=-1))


def test_moe_matches_dense_reference(M):
    moe = make_moe(M, n_experts=5, top_k=2, seed=1)
    x = torch.randn(3, 4, 6)
    out, _ = moe(x)
    assert out.shape == x.shape
    flat = x.reshape(-1, 6)
    logits = moe.gate(flat)
    vals, idx = logits.topk(2, dim=-1)
    w = torch.softmax(vals, dim=-1)
    ref = torch.stack([sum(w[n, j] * moe.experts[int(idx[n, j])](flat[n]) for j in range(2)) for n in range(len(flat))])
    torch.testing.assert_close(out.reshape(-1, 6), ref, atol=1e-5, rtol=1e-4)


def test_experts_only_see_routed_tokens(M):
    moe = make_moe(M, n_experts=4, top_k=1, seed=2)
    x = torch.randn(32, 6)
    rows = {e: 0 for e in range(4)}
    hooks = [exp.register_forward_hook(lambda m, i, o, e=e: rows.__setitem__(e, rows[e] + i[0].shape[0]))
             for e, exp in enumerate(moe.experts)]
    moe(x)
    for h in hooks:
        h.remove()
    top_idx, _, _ = moe.route(x)
    assert rows == {e: int((top_idx == e).sum()) for e in range(4)}, "mỗi expert chỉ chạy trên token được route tới nó"
    assert sum(rows.values()) == 32


def test_gate_gets_gradient(M):
    moe = make_moe(M, n_experts=4, top_k=2, seed=3)
    out, _ = moe(torch.randn(16, 6))
    out.pow(2).sum().backward()
    assert moe.gate.weight.grad is not None and moe.gate.weight.grad.abs().sum() > 0, \
        "router học từ chính output qua trọng số softmax, không chỉ từ loss cân tải"


def test_top1_weight_is_one(M):
    moe = make_moe(M, n_experts=3, top_k=1, seed=4)
    _, weights, _ = moe.route(torch.randn(5, 6))
    torch.testing.assert_close(weights, torch.ones(5, 1))


def test_load_balancing_loss(M):
    probs = torch.full((8, 4), 0.25)
    balanced = torch.tensor([[0], [1], [2], [3], [0], [1], [2], [3]])
    assert M.load_balancing_loss(probs, balanced, 4).item() == pytest.approx(1.0)
    collapsed_p = torch.zeros(8, 4)
    collapsed_p[:, 0] = 1.0
    assert M.load_balancing_loss(collapsed_p, torch.zeros(8, 1, dtype=torch.long), 4).item() == pytest.approx(4.0)
    torch.manual_seed(5)
    p = torch.softmax(torch.randn(6, 3), dim=-1)
    idx = torch.tensor([[0, 1], [0, 2], [1, 2], [0, 1], [0, 2], [0, 1]])
    f = torch.tensor([5, 4, 3]) / 12
    assert M.load_balancing_loss(p, idx, 3).item() == pytest.approx(3 * float((f * p.mean(0)).sum()), rel=1e-5)


def test_discretize_zoh(M):
    A = torch.tensor([-1.0, -4.0])
    B = torch.tensor([2.0, 1.0])
    A_bar, B_bar = M.discretize(A, B, torch.tensor(0.5))
    torch.testing.assert_close(A_bar, torch.tensor([math.exp(-0.5), math.exp(-2.0)]))
    torch.testing.assert_close(B_bar, torch.tensor([(1 - math.exp(-0.5)) * 2.0, (1 - math.exp(-2.0)) / 4.0]),
                               msg="zero-order hold: B_bar = (exp(ΔA) - 1) / A · B")


def test_scan_by_hand(M):
    x = torch.tensor([[1.0], [0.0], [0.0], [2.0]])
    one = torch.ones(4, 1, 1)
    y = M.ssm_scan(0.5 * one, one, one, x)
    torch.testing.assert_close(y, torch.tensor([[1.0], [0.5], [0.25], [2.125]]))


def lti(seed, T=12, D=3, N=4):
    g = torch.Generator().manual_seed(seed)
    A = -torch.rand(D, N, generator=g) * 2 - 0.1
    B = torch.randn(D, N, generator=g)
    C = torch.randn(D, N, generator=g)
    x = torch.randn(T, D, generator=g)
    return A, B, C, x


def test_lti_scan_equals_convolution(M):
    A, B, C, x = lti(6)
    T = x.shape[0]
    A_bar, B_bar = M.discretize(A, B, torch.tensor(0.3))
    y_scan = M.ssm_scan(A_bar.expand(T, -1, -1), B_bar.expand(T, -1, -1), C.expand(T, -1, -1), x)
    K = M.ssm_kernel(A_bar, B_bar, C, T)
    assert K.shape == (T, 3)
    torch.testing.assert_close(K[2], (C * A_bar ** 2 * B_bar).sum(-1))
    torch.testing.assert_close(M.causal_conv(x, K), y_scan, atol=1e-5, rtol=1e-4)


def test_selective_scan_constant_params_is_lti(M):
    A, _, _, x = lti(7)
    T, D = x.shape
    g = torch.Generator().manual_seed(8)
    b, c = torch.randn(4, generator=g), torch.randn(4, generator=g)
    delta = torch.full((T, D), 0.2)
    y = M.selective_scan(x, delta, A, b.expand(T, 4), c.expand(T, 4))
    A_bar, B_bar = M.discretize(A, b.expand(D, 4), torch.tensor(0.2))
    ref = M.ssm_scan(A_bar.expand(T, -1, -1), B_bar.expand(T, -1, -1), c.expand(T, D, 4), x)
    torch.testing.assert_close(y, ref, atol=1e-5, rtol=1e-4)


def test_selective_scan_matches_loop(M):
    A, _, _, x = lti(13, T=7)
    T, D = x.shape
    g = torch.Generator().manual_seed(14)
    B, C = torch.randn(T, 4, generator=g), torch.randn(T, 4, generator=g)
    delta = torch.rand(T, D, generator=g) + 0.05
    h = torch.zeros(D, 4)
    ref = []
    for t in range(T):
        a_bar = torch.exp(delta[t, :, None] * A)
        h = a_bar * h + (a_bar - 1) / A * B[t] * x[t, :, None]
        ref.append(h @ C[t])
    torch.testing.assert_close(M.selective_scan(x, delta, A, B, C), torch.stack(ref), atol=1e-5, rtol=1e-4)


def test_selective_scan_delta_controls_memory(M):
    A, _, _, x = lti(9, T=8)
    T, D = x.shape
    g = torch.Generator().manual_seed(10)
    B, C = torch.randn(T, 4, generator=g), torch.randn(T, 4, generator=g)
    delta = torch.full((T, D), 0.3)
    delta[4] = 50.0
    y = M.selective_scan(x, delta, A, B, C)
    x2 = x.clone()
    x2[:4] += 5.0
    y2 = M.selective_scan(x2, delta, A, B, C)
    assert not torch.allclose(y[:4], y2[:4])
    torch.testing.assert_close(y[4:], y2[4:], atol=1e-5, rtol=1e-4, msg="Δ rất lớn: trạng thái cũ bị xoá (A_bar ≈ 0)")
    delta = torch.full((T, D), 0.3)
    delta[3] = 0.0
    x3 = x.clone()
    x3[3] += 7.0
    y3 = M.selective_scan(x3, delta, A, B, C)
    torch.testing.assert_close(M.selective_scan(x, delta, A, B, C), y3, msg="Δ = 0: bỏ qua input, giữ nguyên trạng thái")


def test_selective_scan_is_causal(M):
    A, _, _, x = lti(11, T=10)
    T, D = x.shape
    g = torch.Generator().manual_seed(12)
    B, C = torch.randn(T, 4, generator=g), torch.randn(T, 4, generator=g)
    delta = torch.rand(T, D, generator=g)
    y = M.selective_scan(x, delta, A, B, C)
    x2 = x.clone()
    x2[6] += 1.0
    y2 = M.selective_scan(x2, delta, A, B, C)
    torch.testing.assert_close(y[:6], y2[:6])
    assert not torch.allclose(y[6:], y2[6:])
