import math

import pytest
import torch
import torch.nn.functional as F
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def M():
    return ex.module("modern.py")


def test_rmsnorm(M):
    torch.manual_seed(0)
    norm = M.RMSNorm(8)
    assert [n for n, _ in norm.named_parameters()] == ["weight"], "RMSNorm chỉ có weight, không có bias"
    with torch.no_grad():
        norm.weight.copy_(torch.linspace(0.5, 2.0, 8))
    x = torch.randn(3, 5, 8) * 4 + 3
    ref = x / torch.sqrt((x * x).mean(-1, keepdim=True) + 1e-6) * norm.weight
    torch.testing.assert_close(norm(x), ref, atol=1e-5, rtol=1e-5)
    y = M.RMSNorm(8)(x)
    assert not torch.allclose(y.mean(-1), torch.zeros(3, 5), atol=1e-2), "RMSNorm không trừ trung bình"


def test_rope_cache_values(M):
    cos, sin = M.rope_cache(4, 6, base=100.0)
    assert cos.shape == (6, 4) and sin.shape == (6, 4)
    freqs = torch.tensor([1.0, 0.1])
    angle = torch.outer(torch.arange(6.0), freqs)
    torch.testing.assert_close(cos[:, :2], angle.cos(), atol=1e-6, rtol=0)
    torch.testing.assert_close(cos[:, 2:], angle.cos(), atol=1e-6, rtol=0)
    torch.testing.assert_close(sin[:, 2:], angle.sin(), atol=1e-6, rtol=0)


def test_apply_rope_pairs_i_with_i_plus_half(M):
    cos, sin = M.rope_cache(4, 3, base=100.0)
    x = torch.tensor([1.0, 2.0, 3.0, 4.0]).view(1, 1, 1, 4).repeat(1, 1, 3, 1)
    out = M.apply_rope(x, cos, sin)
    torch.testing.assert_close(out[0, 0, 0], x[0, 0, 0])
    a, b = 1.0, 0.1
    expected = torch.tensor([
        1 * math.cos(a) - 3 * math.sin(a),
        2 * math.cos(b) - 4 * math.sin(b),
        3 * math.cos(a) + 1 * math.sin(a),
        4 * math.cos(b) + 2 * math.sin(b),
    ])
    torch.testing.assert_close(out[0, 0, 1], expected, atol=1e-5, rtol=0, msg="cặp quay là (i, i + d/2)")


def test_apply_rope_start_pos(M):
    cos, sin = M.rope_cache(8, 16)
    x = torch.randn(2, 3, 4, 8)
    full = M.apply_rope(torch.cat([torch.zeros(2, 3, 5, 8), x], dim=2), cos, sin)[:, :, 5:]
    torch.testing.assert_close(M.apply_rope(x, cos, sin, start_pos=5), full, atol=1e-5, rtol=1e-5)


def test_rope_preserves_norm_and_is_relative(M):
    cos, sin = M.rope_cache(16, 64)
    torch.manual_seed(1)
    q, k = torch.randn(16), torch.randn(16)

    def score(m: int, n: int) -> float:
        qm = M.apply_rope(q.view(1, 1, 1, 16), cos, sin, start_pos=m)
        kn = M.apply_rope(k.view(1, 1, 1, 16), cos, sin, start_pos=n)
        return float((qm * kn).sum())

    rot = M.apply_rope(q.view(1, 1, 1, 16), cos, sin, start_pos=37)
    assert float(rot.norm()) == pytest.approx(float(q.norm()), rel=1e-5), "phép quay giữ nguyên độ dài"
    assert score(10, 3) == pytest.approx(score(40, 33), abs=1e-4), "q·k chỉ phụ thuộc khoảng cách m - n"
    assert score(10, 3) != pytest.approx(score(10, 9), abs=1e-3)


def test_repeat_kv_order(M):
    x = torch.arange(2 * 2 * 3 * 1, dtype=torch.float32).view(2, 2, 3, 1)
    out = M.repeat_kv(x, 3)
    assert out.shape == (2, 6, 3, 1)
    for h in range(6):
        torch.testing.assert_close(out[:, h], x[:, h // 3], msg="head truy vấn h dùng kv head h // n_rep")
    assert M.repeat_kv(x, 1) is x or torch.equal(M.repeat_kv(x, 1), x)


def test_swiglu(M):
    torch.manual_seed(2)
    mlp = M.SwiGLU(6, 10)
    assert {n for n, _ in mlp.named_parameters()} == {"w1.weight", "w2.weight", "w3.weight"}
    x = torch.randn(4, 6)
    ref = mlp.w2(F.silu(mlp.w1(x)) * mlp.w3(x))
    torch.testing.assert_close(mlp(x), ref)


def _reference_attention(attn, x):
    B, T, _ = x.shape
    H, Hkv, D = attn.n_head, attn.n_kv_head, attn.head_dim
    q = attn.wq(x).view(B, T, H, D).transpose(1, 2)
    k = attn.wk(x).view(B, T, Hkv, D).transpose(1, 2)
    v = attn.wv(x).view(B, T, Hkv, D).transpose(1, 2)
    pos = torch.arange(T, dtype=torch.float64)
    inv = 10000.0 ** (-torch.arange(0, D, 2, dtype=torch.float64) / D)
    ang = torch.outer(pos, inv)

    def rope(t):
        t1, t2 = t[..., :D // 2], t[..., D // 2:]
        c, s = ang.cos().float(), ang.sin().float()
        return torch.cat([t1 * c - t2 * s, t2 * c + t1 * s], dim=-1)

    q, k = rope(q), rope(k)
    k = k.repeat_interleave(H // Hkv, dim=1)
    v = v.repeat_interleave(H // Hkv, dim=1)
    y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    return attn.wo(y.transpose(1, 2).reshape(B, T, H * D))


def test_gqa_attention_full_forward(M):
    torch.manual_seed(3)
    attn = M.GQAttention(dim=24, n_head=6, n_kv_head=2, max_len=32)
    assert attn.wk.weight.shape == (8, 24) and attn.wv.weight.shape == (8, 24), "K, V chỉ có n_kv_head head"
    x = torch.randn(2, 10, 24)
    out, cache = attn(x)
    torch.testing.assert_close(out, _reference_attention(attn, x), atol=1e-5, rtol=1e-4)
    k, v = cache
    assert k.shape == (2, 2, 10, 4) and v.shape == (2, 2, 10, 4), "cache lưu K, V TRƯỚC khi repeat (n_kv_head head)"


def test_gqa_attention_is_causal(M):
    torch.manual_seed(4)
    attn = M.GQAttention(dim=16, n_head=4, n_kv_head=4, max_len=16)
    x = torch.randn(1, 8, 16)
    y = x.clone()
    y[0, 5] += 3.0
    a, _ = attn(x)
    b, _ = attn(y)
    torch.testing.assert_close(a[:, :5], b[:, :5])
    assert not torch.allclose(a[:, 5:], b[:, 5:])


def test_kv_cache_decode_matches_full_forward(M):
    torch.manual_seed(5)
    attn = M.GQAttention(dim=32, n_head=4, n_kv_head=2, max_len=32)
    x = torch.randn(2, 12, 32)
    full, _ = attn(x)
    out, cache = attn(x[:, :7])
    pieces = [out]
    for t in range(7, 12):
        step, cache = attn(x[:, t:t + 1], cache)
        pieces.append(step)
    torch.testing.assert_close(torch.cat(pieces, dim=1), full, atol=1e-5, rtol=1e-4)
    assert cache[0].shape == (2, 2, 12, 8)


def test_kv_cache_chunked_prefill(M):
    torch.manual_seed(6)
    attn = M.GQAttention(dim=32, n_head=4, n_kv_head=1, max_len=32)
    x = torch.randn(1, 12, 32)
    full, _ = attn(x)
    a, cache = attn(x[:, :5])
    b, cache = attn(x[:, 5:12], cache)
    torch.testing.assert_close(torch.cat([a, b], dim=1), full, atol=1e-5, rtol=1e-4, msg="thêm nhiều token một lúc vào cache: mask nhân quả phải dịch theo số token đã có")


def test_kv_cache_bytes(M):
    assert M.kv_cache_bytes(32, 8, 128, 8192, batch=1, bytes_per_elem=2) == 1_073_741_824
    assert M.kv_cache_bytes(2, 4, 16, 10, batch=3, bytes_per_elem=4) == 2 * 2 * 4 * 16 * 10 * 3 * 4
