import math

import pytest
import torch
import torch.nn.functional as F

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def at():
    return ex.module("attention.py")


@pytest.fixture
def forbid_builtin(monkeypatch):
    """Không được gọi bản có sẵn của PyTorch bên trong lời giải."""
    def boom(*args, **kwargs):
        raise AssertionError("Không dùng F.scaled_dot_product_attention trong bài này")
    monkeypatch.setattr(F, "scaled_dot_product_attention", boom)
    monkeypatch.setattr(torch.nn.functional, "scaled_dot_product_attention", boom)


def rand_qkv(seed, batch=(2, 3), lq=5, lk=7, d=8, dv=6):
    g = torch.Generator().manual_seed(seed)
    q = torch.randn(*batch, lq, d, generator=g, dtype=torch.float64)
    k = torch.randn(*batch, lk, d, generator=g, dtype=torch.float64)
    v = torch.randn(*batch, lk, dv, generator=g, dtype=torch.float64)
    return q, k, v


@pytest.mark.parametrize("seed", range(3))
def test_matches_pytorch_without_mask(at, seed):
    q, k, v = rand_qkv(seed)
    ref = F.scaled_dot_product_attention(q, k, v)
    out, weights = at.scaled_dot_product_attention(q, k, v)
    torch.testing.assert_close(out, ref)
    assert weights.shape == (2, 3, 5, 7)
    torch.testing.assert_close(weights.sum(-1), torch.ones(2, 3, 5, dtype=torch.float64))


def test_does_not_call_builtin(at, forbid_builtin):
    q, k, v = rand_qkv(0)
    out, _ = at.scaled_dot_product_attention(q, k, v)
    assert out.shape == (2, 3, 5, 6)


def test_weights_are_softmax_of_scaled_scores(at):
    q, k, v = rand_qkv(1, batch=(), lq=3, lk=4, d=16, dv=2)
    _, weights = at.scaled_dot_product_attention(q, k, v)
    expected = torch.softmax(q @ k.T / math.sqrt(16), dim=-1)    # chia sqrt(d_k), không phải d_k
    torch.testing.assert_close(weights, expected)


def test_causal_mask_shape_and_values(at):
    m = at.causal_mask(4)
    assert m.dtype == torch.bool
    assert m.tolist() == [[True, False, False, False],
                          [True, True, False, False],
                          [True, True, True, False],
                          [True, True, True, True]]


def test_causal_matches_pytorch(at):
    q, k, v = rand_qkv(2, lq=6, lk=6)
    ref = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    out, weights = at.scaled_dot_product_attention(q, k, v, mask=at.causal_mask(6))
    torch.testing.assert_close(out, ref)
    assert torch.all(weights.triu(diagonal=1) == 0)              # tương lai có trọng số đúng 0


def test_causal_output_ignores_future_tokens(at):
    q, k, v = rand_qkv(3, batch=(1,), lq=6, lk=6)
    mask = at.causal_mask(6)
    out, _ = at.scaled_dot_product_attention(q, k, v, mask=mask)
    k2, v2 = k.clone(), v.clone()
    k2[:, 4:] += 5.0                                             # đổi token 4, 5
    v2[:, 4:] -= 3.0
    out2, _ = at.scaled_dot_product_attention(q, k2, v2, mask=mask)
    torch.testing.assert_close(out[:, :4], out2[:, :4])          # vị trí 0..3 không thấy tương lai
    assert not torch.allclose(out[:, 4:], out2[:, 4:])


def test_padding_mask_values(at):
    m = at.padding_mask(torch.tensor([2, 4, 1]), max_len=4)
    assert m.dtype == torch.bool
    assert m.tolist() == [[True, True, False, False],
                          [True, True, True, True],
                          [True, False, False, False]]


def test_padding_mask_hides_padded_keys(at):
    q, k, v = rand_qkv(4, batch=(3,), lq=5, lk=5)
    lengths = torch.tensor([5, 3, 2])
    key_mask = at.padding_mask(lengths, 5)[:, None, :]           # (B, 1, Lk): mọi query cùng mask
    out, weights = at.scaled_dot_product_attention(q, k, v, mask=key_mask)
    ref = F.scaled_dot_product_attention(q, k, v, attn_mask=key_mask)
    torch.testing.assert_close(out, ref)
    for b, n in enumerate(lengths.tolist()):
        assert torch.all(weights[b, :, n:] == 0)
    v2 = v.clone()
    v2[1, 3:] = 100.0                                            # rác ở vị trí padding
    out2, _ = at.scaled_dot_product_attention(q, k, v2, mask=key_mask)
    torch.testing.assert_close(out, out2)


def test_numerically_stable_for_large_scores(at):
    q, k, v = rand_qkv(5, batch=(2,), lq=4, lk=4, d=8)
    q = q.float() * 1e3                                          # điểm số cỡ 1e4: exp tràn nếu không trừ max
    k, v = k.float(), v.float()
    out, weights = at.scaled_dot_product_attention(q, k, v)
    assert torch.isfinite(out).all() and torch.isfinite(weights).all()
    torch.testing.assert_close(out, F.scaled_dot_product_attention(q, k, v))


def test_gradients_flow_like_pytorch(at):
    q, k, v = rand_qkv(6, batch=(2,), lq=3, lk=4)
    tensors = [t.clone().requires_grad_(True) for t in (q, k, v)]
    out, _ = at.scaled_dot_product_attention(*tensors)
    out.square().sum().backward()
    refs = [t.clone().requires_grad_(True) for t in (q, k, v)]
    F.scaled_dot_product_attention(*refs).square().sum().backward()
    for mine, ref in zip(tensors, refs):
        torch.testing.assert_close(mine.grad, ref.grad)
