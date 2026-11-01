import importlib.util
import sys

import pytest
import torch
from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)
GPT_FILE = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"
V, T = 23, 9


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("patching.ipynb")


@pytest.fixture(scope="module")
def G():
    spec = importlib.util.spec_from_file_location("m08_i02_gpt", GPT_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tiny(G, n_layer=3, seed=0):
    torch.manual_seed(seed)
    model = G.GPT(G.GPTConfig(vocab_size=V, block_size=12, n_layer=n_layer, n_head=3, n_embd=12)).eval()
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith("bias"):
                p.add_(torch.randn_like(p) * 0.3)
            if name.endswith("proj.weight"):
                p.mul_(8)
            if "qkv.weight" in name or "emb" in name:
                p.mul_(15)
    return model


def cache_of(model, idx):
    """Cache tối thiểu theo tên khoá của bài Basic 01, tự dựng trong test."""
    cache, handles = {}, []
    H = model.config.n_head
    for l, b in enumerate(model.blocks):
        handles.append(b.register_forward_pre_hook(lambda m, a, l=l: cache.__setitem__(f"resid_pre.{l}", a[0].detach().clone())))
        handles.append(b.attn.register_forward_hook(lambda m, a, o, l=l: cache.__setitem__(f"attn_out.{l}", o.detach().clone())))
        handles.append(b.mlp.register_forward_hook(lambda m, a, o, l=l: cache.__setitem__(f"mlp_out.{l}", o.detach().clone())))
        handles.append(b.attn.proj.register_forward_pre_hook(
            lambda m, a, l=l: cache.__setitem__(f"z.{l}", a[0].detach().clone().view(*a[0].shape[:2], H, -1))))
    with torch.no_grad():
        logits, _ = model(idx)
    for h in handles:
        h.remove()
    return logits, cache


def pair(k=4, seed=1):
    g = torch.Generator().manual_seed(seed)
    clean = torch.randint(V, (2, T), generator=g)
    corrupt = clean.clone()
    corrupt[:, k] = (clean[:, k] + 5) % V
    return clean, corrupt


def all_hooks(model):
    return sum(len(m._forward_hooks) + len(m._forward_pre_hooks) for m in model.modules())


def test_logit_diff_and_normalized_effect(nb):
    logits = torch.zeros(2, 3, 5)
    logits[0, -1, 1], logits[0, -1, 3] = 2.0, -1.0
    logits[1, -1, 4], logits[1, 0, 0] = 1.5, 9.0
    ld = nb.logit_diff(logits, torch.tensor([1, 4]), torch.tensor([3, 0]))
    torch.testing.assert_close(ld, torch.tensor([3.0, 1.5]), msg="chỉ dùng vị trí cuối")
    assert nb.normalized_effect(1.0, 3.0, -1.0) == pytest.approx(0.5)
    assert nb.normalized_effect(-1.0, 3.0, -1.0) == pytest.approx(0.0)
    assert nb.normalized_effect(3.0, 3.0, -1.0) == pytest.approx(1.0)


def test_patch_resid_layer0_at_differing_position_restores_clean(nb, G):
    model = tiny(G)
    clean, corrupt = pair(k=4)
    clean_logits, clean_cache = cache_of(model, clean)
    corrupt_logits, _ = cache_of(model, corrupt)
    out = nb.patch_resid_pre(model, corrupt, clean_cache, 0, 4)
    torch.testing.assert_close(out, clean_logits, atol=1e-5, rtol=1e-5,
                               msg="ở tầng 0 hai input chỉ khác ở vị trí 4: patch vị trí đó phải ra đúng run clean")
    out_all = nb.patch_resid_pre(model, corrupt, clean_cache, 2, None)
    torch.testing.assert_close(out_all, clean_logits, atol=1e-5, rtol=1e-5, msg="pos=None: mọi vị trí")
    assert all_hooks(model) == 0


def test_patch_resid_respects_causality_and_position(nb, G):
    model = tiny(G)
    clean, corrupt = pair(k=3)
    _, clean_cache = cache_of(model, clean)
    corrupt_logits, _ = cache_of(model, corrupt)
    out = nb.patch_resid_pre(model, corrupt, clean_cache, 1, 6)
    torch.testing.assert_close(out[:, :6], corrupt_logits[:, :6], atol=1e-6, rtol=1e-6, msg="vị trí trước pos không đổi")
    assert not torch.allclose(out[:, 6:], corrupt_logits[:, 6:], atol=1e-4), "vị trí pos trở đi phải đổi"
    same = nb.patch_resid_pre(model, corrupt, clean_cache, 2, 1)
    torch.testing.assert_close(same, corrupt_logits, atol=1e-6, rtol=1e-6, msg="trước vị trí khác nhau, stream hai run trùng nhau")


def test_patch_head_matches_manual(nb, G):
    model = tiny(G)
    clean, corrupt = pair(k=2)
    _, clean_cache = cache_of(model, clean)
    for layer, head, pos in [(1, 2, None), (2, 0, 7), (0, 1, 2)]:
        src = clean_cache[f"z.{layer}"]

        def hook(m, a):
            z = a[0].clone().view(2, T, 3, 4)
            where = slice(None) if pos is None else pos
            z[:, where, head] = src[:, where, head]
            return (z.view(2, T, 12),)

        h = model.blocks[layer].attn.proj.register_forward_pre_hook(hook)
        with torch.no_grad():
            ref, _ = model(corrupt)
        h.remove()
        out = nb.patch_head(model, corrupt, clean_cache, layer, head, pos)
        torch.testing.assert_close(out, ref, atol=1e-5, rtol=1e-5, msg=f"tầng {layer}, head {head}, pos {pos}")
    assert all_hooks(model) == 0


def test_patch_sublayer_matches_manual(nb, G):
    model = tiny(G, n_layer=1)
    clean, corrupt = pair(k=5)
    _, clean_cache = cache_of(model, clean)
    b = model.blocks[0]
    with torch.no_grad():
        x = model.tok_emb(corrupt) + model.pos_emb(torch.arange(T))
        x_attn = x + clean_cache["attn_out.0"]
        ref_attn = model.lm_head(model.ln_f(x_attn + b.mlp(b.ln2(x_attn))))
        x_mid = x + b.attn(b.ln1(x))
        ref_mlp = model.lm_head(model.ln_f(x_mid + clean_cache["mlp_out.0"]))
    torch.testing.assert_close(nb.patch_sublayer(model, corrupt, clean_cache, "attn", 0), ref_attn, atol=1e-5, rtol=1e-5)
    torch.testing.assert_close(nb.patch_sublayer(model, corrupt, clean_cache, "mlp", 0), ref_mlp, atol=1e-5, rtol=1e-5)
    assert all_hooks(model) == 0


def test_resid_patching_sweep(nb, G):
    model = tiny(G)
    k = 4
    clean, corrupt = pair(k=k)
    clean_logits, clean_cache = cache_of(model, clean)
    corrupt_logits, _ = cache_of(model, corrupt)
    io, s = torch.tensor([1, 2]), torch.tensor([3, 4])
    metric = lambda lg: (lg[:, -1, io] - lg[:, -1, s]).diagonal().mean().item()
    cv, xv = metric(clean_logits), metric(corrupt_logits)
    assert abs(cv - xv) > 0.01, "dữ liệu test phải tách được hai run"
    table = nb.resid_patching_sweep(model, corrupt, clean_cache, metric, cv, xv)
    assert tuple(table.shape) == (3, T)
    expected_row0 = torch.zeros(T)
    expected_row0[k] = 1.0
    torch.testing.assert_close(table[0].float(), expected_row0, atol=1e-4, rtol=0, msg="tầng 0: chỉ vị trí khác nhau có hiệu ứng, bằng 1")
    torch.testing.assert_close(table[:, :k].float(), torch.zeros(3, k), atol=1e-4, rtol=0, msg="vị trí trước chỗ khác nhau: 0 ở mọi tầng")
    last = nb.normalized_effect(metric(nb.patch_resid_pre(model, corrupt, clean_cache, 2, T - 1)), cv, xv)
    assert float(table[2, T - 1]) == pytest.approx(last, abs=1e-5)
