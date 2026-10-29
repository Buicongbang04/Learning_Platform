import math

import pytest
import torch
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="module")
def tm():
    return ex.module("transformer.py")


def test_positional_encoding_formula(tm):
    pe = tm.sinusoidal_positional_encoding(max_len=50, d_model=16)
    assert pe.shape == (50, 16)
    for pos in (0, 7, 49):
        for i in range(8):
            angle = pos / 10000 ** (2 * i / 16)
            assert pe[pos, 2 * i].item() == pytest.approx(math.sin(angle), abs=1e-5)
            assert pe[pos, 2 * i + 1].item() == pytest.approx(math.cos(angle), abs=1e-5)


def test_attention_matches_pytorch_multihead(tm):
    torch.manual_seed(0)
    mine = tm.MultiHeadSelfAttention(d_model=16, n_heads=4)
    ref = nn.MultiheadAttention(16, 4, batch_first=True)
    with torch.no_grad():                                   # q, k, v xếp chồng theo hàng như PyTorch
        ref.in_proj_weight.copy_(mine.qkv.weight)
        ref.in_proj_bias.copy_(mine.qkv.bias)
        ref.out_proj.weight.copy_(mine.out.weight)
        ref.out_proj.bias.copy_(mine.out.bias)
    mine.eval(), ref.eval()
    x = torch.randn(3, 7, 16)
    pad = torch.tensor([[False] * 7, [False] * 4 + [True] * 3, [False] * 2 + [True] * 5])   # True = padding
    expected, _ = ref(x, x, x, need_weights=False)
    torch.testing.assert_close(mine(x), expected, rtol=1e-5, atol=1e-5)
    expected, _ = ref(x, x, x, key_padding_mask=pad, need_weights=False)
    torch.testing.assert_close(mine(x, key_padding_mask=pad), expected, rtol=1e-5, atol=1e-5)


def test_attention_rejects_bad_heads(tm):
    with pytest.raises(ValueError):
        tm.MultiHeadSelfAttention(d_model=10, n_heads=4)


def test_encoder_block_is_permutation_equivariant(tm):
    torch.manual_seed(1)
    block = tm.EncoderBlock(d_model=16, n_heads=4, d_ff=32)
    block.eval()
    x = torch.randn(2, 6, 16)
    perm = torch.tensor([3, 0, 5, 1, 4, 2])
    out = block(x)
    assert out.shape == x.shape
    # không có positional encoding, attention không biết thứ tự: hoán vị vào = hoán vị ra
    torch.testing.assert_close(block(x[:, perm]), out[:, perm], rtol=1e-5, atol=1e-5)


def test_encoder_block_ignores_padding(tm):
    torch.manual_seed(2)
    block = tm.EncoderBlock(d_model=16, n_heads=2, d_ff=32)
    block.eval()
    x = torch.randn(1, 4, 16)
    out = block(x)
    padded = torch.cat([x, torch.randn(1, 3, 16) * 10], dim=1)
    mask = torch.tensor([[False] * 4 + [True] * 3])
    torch.testing.assert_close(block(padded, key_padding_mask=mask)[:, :4], out, rtol=1e-5, atol=1e-5)


def test_encoder_block_has_residual_and_layernorm(tm):
    block = tm.EncoderBlock(d_model=16, n_heads=4, d_ff=32)
    assert sum(isinstance(m, nn.LayerNorm) for m in block.modules()) >= 2
    with torch.no_grad():                                    # tắt hai nhánh: còn lại đúng phần residual
        for p in block.parameters():
            p.zero_()
    x = torch.randn(2, 5, 16)
    torch.testing.assert_close(block(x), x)


def test_classifier_padding_and_order(tm):
    torch.manual_seed(3)
    model = tm.TransformerClassifier(vocab_size=20, d_model=16, n_heads=4, n_layers=2, d_ff=32, max_len=16, dropout=0.1)
    model.eval()
    ids = torch.tensor([[5, 6, 7, 8, 0, 0], [9, 10, 0, 0, 0, 0]])
    out = model(ids)
    assert out.shape == (2,)
    wider = torch.cat([ids, torch.zeros(2, 4, dtype=torch.long)], dim=1)
    torch.testing.assert_close(model(wider), out, rtol=1e-5, atol=1e-5)
    reversed_ids = torch.tensor([[8, 7, 6, 5, 0, 0], [10, 9, 0, 0, 0, 0]])
    assert not torch.allclose(model(reversed_ids), out, atol=1e-4)     # có positional encoding: thứ tự có nghĩa


def order_task(n, seed, length=10, vocab=20):
    """Mỗi chuỗi chứa token 2 và token 3 đúng một lần; nhãn = 2 đứng trước 3.

    Túi từ (bag of words) của hai lớp giống hệt nhau, chỉ model nhìn thứ tự mới làm được.
    """
    g = torch.Generator().manual_seed(seed)
    X = torch.randint(4, vocab, (n, length), generator=g)
    for i in range(n):
        a, b = torch.randperm(length, generator=g)[:2].tolist()
        X[i, a], X[i, b] = 2, 3
    y = ((X == 2).float().argmax(1) < (X == 3).float().argmax(1)).float()
    return X, y


def test_classifier_learns_word_order(tm):
    X, y = order_task(2000, 0)
    Xt, yt = order_task(500, 1)
    torch.manual_seed(0)
    model = tm.TransformerClassifier(vocab_size=20, d_model=32, n_heads=4, n_layers=2, d_ff=64, max_len=16, dropout=0.0)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    loss_fn = nn.BCEWithLogitsLoss()
    g = torch.Generator().manual_seed(0)
    for _ in range(20):
        model.train()
        for idx in torch.randperm(len(X), generator=g).split(64):
            opt.zero_grad()
            loss_fn(model(X[idx]), y[idx]).backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        acc = ((model(Xt) > 0).float() == yt).float().mean().item()
    assert acc > 0.9                     # bản tham chiếu: 0.966–1.000 trên 10 seed


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 400
