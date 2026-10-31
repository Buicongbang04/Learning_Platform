import dataclasses
import re

import pytest
import torch
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ablation.ipynb")


def make(nb, **kw):
    cfg = dict(vocab_size=40, block_size=24, n_layer=2, n_head=4, n_kv_head=2, n_embd=32, ffn_hidden=64)
    cfg.update(kw)
    torch.manual_seed(0)
    return nb.ModernGPT(nb.ModernConfig(**cfg)).eval()


def test_config_defaults(nb):
    fields = {f.name: f.default for f in dataclasses.fields(nb.ModernConfig)}
    assert fields == {"vocab_size": 8000, "block_size": 128, "n_layer": 4, "n_head": 4, "n_kv_head": 2, "n_embd": 256,
                      "ffn_hidden": 704, "pos": "rope", "norm": "rms", "mlp": "swiglu"}


def n_params(model):
    return sum(p.numel() for p in model.parameters())


def test_param_counts_follow_flags(nb):
    d, L, V, hd = 32, 2, 40, 8
    base = make(nb)
    attn = d * d * 2 + 2 * (d * 2 * hd)
    expected = V * d + L * (2 * d + attn + 3 * d * 64) + d
    assert n_params(base) == expected, "RMSNorm chỉ có weight; GQA: wk, wv có n_kv_head head; lm_head dùng chung tok_emb"
    assert base.lm_head.weight is base.tok_emb.weight and base.pos_emb is None
    assert n_params(make(nb, n_kv_head=4)) - expected == L * 2 * d * 2 * hd
    assert n_params(make(nb, pos="learned")) - expected == 24 * d
    assert n_params(make(nb, norm="layer")) - expected == (2 * L + 1) * d
    assert n_params(make(nb, mlp="gelu")) - expected == L * (2 * d * 4 * d - 3 * d * 64)


def test_forward_and_loss(nb):
    model = make(nb)
    idx = torch.randint(0, 40, (2, 10), generator=torch.Generator().manual_seed(1))
    logits, loss, caches = model(idx, idx)
    assert logits.shape == (2, 10, 40) and loss.shape == ()
    torch.testing.assert_close(loss, torch.nn.functional.cross_entropy(logits.reshape(-1, 40), idx.reshape(-1)))
    assert len(caches) == 2 and caches[0][0].shape == (2, 2, 10, 8), "cache mỗi tầng có n_kv_head head"


@pytest.mark.parametrize("flags", [{}, {"pos": "learned"}, {"n_kv_head": 1, "norm": "layer", "mlp": "gelu"}])
def test_causal(nb, flags):
    model = make(nb, **flags)
    idx = torch.randint(0, 40, (1, 12), generator=torch.Generator().manual_seed(2))
    changed = idx.clone()
    changed[0, 6] = (changed[0, 6] + 1) % 40
    a, _, _ = model(idx)
    b, _, _ = model(changed)
    torch.testing.assert_close(a[:, :6], b[:, :6])


@pytest.mark.parametrize("flags", [{}, {"pos": "learned"}, {"n_kv_head": 1}, {"n_kv_head": 4, "norm": "layer"}])
def test_cached_decode_matches_full(nb, flags):
    model = make(nb, **flags)
    idx = torch.randint(0, 40, (2, 15), generator=torch.Generator().manual_seed(3))
    full, _, _ = model(idx)
    out, _, caches = model(idx[:, :9], caches=[None, None])
    pieces = [out]
    for t in range(9, 15):
        step, _, caches = model(idx[:, t:t + 1], caches=caches)
        pieces.append(step)
    torch.testing.assert_close(torch.cat(pieces, 1), full, atol=1e-5, rtol=1e-4,
                               msg="vị trí của token mới (RoPE hoặc pos_emb) bắt đầu từ số token trong cache")


@pytest.mark.parametrize("flags", [{}, {"pos": "learned"}])
def test_generate_cache_equals_no_cache(nb, flags):
    model = make(nb, **flags).train()
    start = torch.tensor([[1, 2, 3, 4]])
    a = model.generate(start, 16, temperature=0, use_cache=True)
    b = model.generate(start, 16, temperature=0, use_cache=False)
    assert a.shape == (1, 20) and torch.equal(a, b)
    assert model.training
    s1 = model.generate(start, 10, temperature=1.0, top_k=5, generator=torch.Generator().manual_seed(4))
    s2 = model.generate(start, 10, temperature=1.0, top_k=5, generator=torch.Generator().manual_seed(4), use_cache=False)
    assert torch.equal(s1, s2)


def test_generate_with_cache_feeds_one_token(nb):
    model = make(nb)
    lengths = []
    handle = model.tok_emb.register_forward_hook(lambda m, i, o: lengths.append(i[0].shape[1]) and None)
    model.generate(torch.tensor([[1, 2, 3]]), 4, temperature=0, use_cache=True)
    handle.remove()
    assert lengths[0] == 3 and all(n == 1 for n in lengths[1:]), "prefill một lần, rồi mỗi bước một token"


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 500, "báo cáo: ít nhất 500 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng ablation"
    assert re.search(r"bpc|bits?[- ]per[- ]char", doc, re.I)
    assert re.search(r"seed", doc, re.I), "báo cáo phải nói về độ nhiễu giữa các seed"
