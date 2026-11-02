import importlib.util
import sys

import pytest
import torch
from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)
GPT_FILE = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"


@pytest.fixture(scope="module")
def G():
    spec = importlib.util.spec_from_file_location("m08_b01_gpt", GPT_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hk():
    return ex.module("hooks.py")


def tiny(G, seed=0, **kw):
    cfg = dict(vocab_size=40, block_size=12, n_layer=3, n_head=4, n_embd=24)
    cfg.update(kw)
    torch.manual_seed(seed)
    model = G.GPT(G.GPTConfig(**cfg)).eval()
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith("bias") or "ln" in name:
                p.add_(torch.randn_like(p) * 0.3)
            if name.endswith("proj.weight"):
                p.mul_(10)
    return model


def batch(seed=1, B=2, T=9, V=40):
    return torch.randint(V, (B, T), generator=torch.Generator().manual_seed(seed))


def all_hooks(model):
    return sum(len(m._forward_hooks) + len(m._forward_pre_hooks) for m in model.modules())


def test_keys_and_shapes(G, hk):
    model, idx = tiny(G), batch()
    logits, cache = hk.run_with_cache(model, idx)
    assert logits.shape == (2, 9, 40)
    for l in range(3):
        for k in ["resid_pre", "attn_out", "resid_mid", "mlp_out", "resid_post"]:
            assert cache[f"{k}.{l}"].shape == (2, 9, 24), f"{k}.{l}"
        assert cache[f"pattern.{l}"].shape == (2, 4, 9, 9)
        assert cache[f"z.{l}"].shape == (2, 9, 4, 6), "z.l shape (B, T, n_head, head_dim)"


def test_resid_pre_0_is_embedding_not_normalized(G, hk):
    model, idx = tiny(G), batch()
    _, cache = hk.run_with_cache(model, idx)
    with torch.no_grad():
        emb = model.tok_emb(idx) + model.pos_emb(torch.arange(idx.shape[1]))
    torch.testing.assert_close(cache["resid_pre.0"], emb, msg="resid_pre.0 là stream trước ln1 (tok_emb + pos_emb)")


def test_residual_bookkeeping(G, hk):
    model, idx = tiny(G), batch()
    logits, cache = hk.run_with_cache(model, idx)
    for l in range(3):
        torch.testing.assert_close(cache[f"resid_mid.{l}"], cache[f"resid_pre.{l}"] + cache[f"attn_out.{l}"], atol=1e-5, rtol=1e-5)
        torch.testing.assert_close(cache[f"resid_post.{l}"], cache[f"resid_mid.{l}"] + cache[f"mlp_out.{l}"], atol=1e-5, rtol=1e-5)
        if l < 2:
            torch.testing.assert_close(cache[f"resid_pre.{l + 1}"], cache[f"resid_post.{l}"])
    with torch.no_grad():
        torch.testing.assert_close(model.lm_head(model.ln_f(cache["resid_post.2"])), logits, atol=1e-5, rtol=1e-5)


def test_attn_and_mlp_out_are_sublayer_outputs(G, hk):
    model, idx = tiny(G), batch()
    _, cache = hk.run_with_cache(model, idx)
    with torch.no_grad():
        for l, block in enumerate(model.blocks):
            torch.testing.assert_close(cache[f"attn_out.{l}"], block.attn(block.ln1(cache[f"resid_pre.{l}"])), atol=1e-5, rtol=1e-5)
            torch.testing.assert_close(cache[f"mlp_out.{l}"], block.mlp(block.ln2(cache[f"resid_mid.{l}"])), atol=1e-5, rtol=1e-5)


def test_pattern_is_causal_softmax(G, hk):
    model, idx = tiny(G), batch()
    _, cache = hk.run_with_cache(model, idx)
    with torch.no_grad():
        attn = model.blocks[1].attn
        x = model.blocks[1].ln1(cache["resid_pre.1"])
        q, k, _ = attn.qkv(x).split(24, dim=2)
        q, k = (t.view(2, 9, 4, 6).transpose(1, 2) for t in (q, k))
        s = (q @ k.transpose(-2, -1)) / 6 ** 0.5
        s = s.masked_fill(~torch.tril(torch.ones(9, 9, dtype=torch.bool)), float("-inf"))
        torch.testing.assert_close(cache["pattern.1"], torch.softmax(s, -1), atol=1e-5, rtol=1e-5)


def test_eval_no_grad_and_mode_restored(G, hk):
    model, idx = tiny(G, dropout=0.5), batch()
    model.train()
    with torch.enable_grad():
        logits, cache = hk.run_with_cache(model, idx)
    assert model.training, "trả lại chế độ train/eval như trước khi gọi"
    assert not logits.requires_grad and not any(v.requires_grad for v in cache.values()), "cache không giữ graph"
    torch.testing.assert_close(cache["pattern.0"].sum(-1), torch.ones(2, 4, 9), msg="chạy ở chế độ eval (dropout tắt)")
    model.eval()
    ref, _ = model(idx)
    torch.testing.assert_close(logits, ref.detach())


def test_hooks_removed_even_on_error(G, hk):
    model = tiny(G)
    hk.run_with_cache(model, batch())
    assert all_hooks(model) == 0, "gỡ mọi hook sau khi chạy"
    with pytest.raises(ValueError):
        hk.run_with_cache(model, torch.zeros(1, 13, dtype=torch.long))
    assert all_hooks(model) == 0, "gỡ hook cả khi forward lỗi (try/finally)"


def test_head_contributions_sum_to_attn_out(G, hk):
    model, idx = tiny(G), batch()
    _, cache = hk.run_with_cache(model, idx)
    for l in range(3):
        hc = hk.head_contributions(model, cache, l)
        assert hc.shape == (2, 9, 4, 24)
        total = hc.sum(dim=2) + model.blocks[l].attn.proj.bias.detach()
        torch.testing.assert_close(total, cache[f"attn_out.{l}"], atol=1e-5, rtol=1e-5)


def test_head_contribution_equals_removing_that_head(G, hk):
    model, idx = tiny(G), batch()
    _, cache = hk.run_with_cache(model, idx)
    hc = hk.head_contributions(model, cache, 1)
    proj = model.blocks[1].attn.proj
    for h in range(4):
        z = cache["z.1"].clone()
        z[:, :, h] = 0
        with torch.no_grad():
            without = proj(z.reshape(2, 9, 24))
        torch.testing.assert_close(hc[:, :, h], cache["attn_out.1"] - without, atol=1e-5, rtol=1e-5,
                                   msg=f"head {h}: cột h*head_dim..(h+1)*head_dim của proj")


def test_residual_components_sum_to_final_stream(G, hk):
    model, idx = tiny(G), batch()
    _, cache = hk.run_with_cache(model, idx)
    parts = hk.residual_components(model, cache, idx)
    assert list(parts) == ["tok_emb", "pos_emb", "attn_out.0", "mlp_out.0", "attn_out.1", "mlp_out.1", "attn_out.2", "mlp_out.2"]
    assert all(v.shape == (2, 9, 24) for v in parts.values())
    torch.testing.assert_close(sum(parts.values()), cache["resid_post.2"], atol=1e-5, rtol=1e-5)
