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
    spec = importlib.util.spec_from_file_location("m08_b02_gpt", GPT_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def lens():
    return ex.module("lens.py")


def tiny(G, seed=0):
    torch.manual_seed(seed)
    model = G.GPT(G.GPTConfig(vocab_size=30, block_size=16, n_layer=2, n_head=2, n_embd=16)).eval()
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith("bias") or "ln" in name:
                p.add_(torch.randn_like(p) * 0.5)
            if name.endswith("proj.weight"):
                p.mul_(10)
    return model


def offset_pattern(T, offsets, fallback_self=True):
    """Pattern (1, H, T, T): head h đặt toàn bộ attention của vị trí t vào t - offsets[h] (nếu hợp lệ, không thì vào t)."""
    pat = torch.zeros(1, len(offsets), T, T)
    for h, off in enumerate(offsets):
        for t in range(T):
            k = t - off
            pat[0, h, t, k if 0 <= k <= t else t] = 1.0
    return pat


def test_repeated_tokens(lens):
    seq = lens.repeated_tokens(100, 6, 3, torch.Generator().manual_seed(0))
    assert seq.shape == (3, 12)
    assert torch.equal(seq[:, :6], seq[:, 6:])
    ref = torch.randint(100, (3, 6), generator=torch.Generator().manual_seed(0))
    assert torch.equal(seq[:, :6], ref), "một lệnh torch.randint(vocab_size, (batch, half), generator=generator)"
    pre = lens.repeated_tokens(100, 6, 3, torch.Generator().manual_seed(0), prefix=99)
    assert pre.shape == (3, 13) and torch.all(pre[:, 0] == 99) and torch.equal(pre[:, 1:], seq)


def test_prev_token_score(lens):
    T = 8
    pat = offset_pattern(T, [1, 0])
    uniform = torch.tril(torch.ones(T, T))
    uniform = (uniform / uniform.sum(-1, keepdim=True)).view(1, 1, T, T)
    pat = torch.cat([pat, uniform], dim=1).repeat(2, 1, 1, 1)
    score = lens.prev_token_score(pat)
    assert score.shape == (3,)
    expected = torch.tensor([1.0, 0.0, sum(1 / (t + 1) for t in range(1, T)) / (T - 1)])
    torch.testing.assert_close(score, expected, msg="trung bình trên t = 1..T-1, mọi phần tử batch")


@pytest.mark.parametrize("prefix", [0, 1, 3])
def test_induction_and_duplicate_scores(lens, prefix):
    half = 5
    T = prefix + 2 * half
    pat = offset_pattern(T, [half - 1, half, 1])
    ind = lens.induction_score(pat, half)
    dup = lens.duplicate_token_score(pat, half)
    torch.testing.assert_close(ind, torch.tensor([1.0, 0.0, 0.0]), msg="induction: từ t tới t - half + 1, t ở nửa sau")
    torch.testing.assert_close(dup, torch.tensor([0.0, 1.0, 0.0]), msg="duplicate: từ t tới t - half, t ở nửa sau")


def test_induction_score_averages_second_half_only(lens):
    half, T = 4, 9
    pat = offset_pattern(T, [half - 1])
    pat[0, 0, :5] = 0
    pat[0, 0, torch.arange(5), torch.arange(5)] = 1.0
    pat[0, 0, 6] = 0
    pat[0, 0, 6, 6] = 1.0
    torch.testing.assert_close(lens.induction_score(pat, half), torch.tensor([0.75]))


def test_logit_lens_applies_final_layernorm(G, lens):
    model = tiny(G)
    idx = torch.randint(30, (2, 7), generator=torch.Generator().manual_seed(1))
    resid = {}
    h = model.ln_f.register_forward_pre_hook(lambda m, a: resid.__setitem__("final", a[0].detach()))
    with torch.no_grad():
        logits, _ = model(idx)
    h.remove()
    out = lens.logit_lens(model, resid["final"])
    torch.testing.assert_close(out, logits, atol=1e-5, rtol=1e-5, msg="ở stream cuối, logit lens phải bằng logits của model")
    x = torch.randn(2, 7, 16) * 3 + 1
    with torch.no_grad():
        torch.testing.assert_close(lens.logit_lens(model, x), model.lm_head(model.ln_f(x)), atol=1e-5, rtol=1e-5)
    assert not lens.logit_lens(model, x).requires_grad


def test_token_rank(lens):
    logits = torch.tensor([[3.0, 1.0, 3.0, 0.0], [0.5, 2.0, -1.0, 4.0]])
    ranks = lens.token_rank(logits, torch.tensor([2, 0]))
    assert ranks.tolist() == [0, 2]
    ranks3 = lens.token_rank(logits.unsqueeze(0).repeat(2, 1, 1), torch.tensor([[1, 3], [3, 2]]))
    assert ranks3.tolist() == [[2, 0], [3, 3]]


def components_by_hand(model, idx):
    parts, handles = {}, []
    for l, block in enumerate(model.blocks):
        handles.append(block.attn.register_forward_hook(lambda m, a, o, l=l: parts.__setitem__(f"attn.{l}", o.detach())))
        handles.append(block.mlp.register_forward_hook(lambda m, a, o, l=l: parts.__setitem__(f"mlp.{l}", o.detach())))
    with torch.no_grad():
        model(idx)
        emb = {"tok": model.tok_emb(idx), "pos": model.pos_emb(torch.arange(idx.shape[1])).expand(idx.shape[0], -1, -1)}
    for h in handles:
        h.remove()
    return {**emb, **parts}


def test_direct_logit_attribution_sums_to_logit_difference(G, lens):
    model = tiny(G)
    idx = torch.randint(30, (2, 7), generator=torch.Generator().manual_seed(2))
    comps = components_by_hand(model, idx)
    final = sum(comps.values())
    a, b = 4, 11
    direction = (model.lm_head.weight[a] - model.lm_head.weight[b]).detach()
    dla = lens.direct_logit_attribution(model, comps, final, direction)
    assert set(dla) == set(comps) and all(v.shape == (2, 7) for v in dla.values())
    with torch.no_grad():
        logits = model.lm_head(model.ln_f(final))
        total = sum(dla.values()) + model.ln_f.bias @ direction
    torch.testing.assert_close(total, logits[..., a] - logits[..., b], atol=1e-4, rtol=1e-4,
                               msg="tổng DLA + ln_f.bias·direction = logit[a] - logit[b]")


def test_direct_logit_attribution_is_linear_per_component(G, lens):
    model = tiny(G)
    idx = torch.randint(30, (1, 6), generator=torch.Generator().manual_seed(3))
    comps = components_by_hand(model, idx)
    final = sum(comps.values())
    direction = torch.randn(16)
    one = lens.direct_logit_attribution(model, {"x": comps["attn.1"]}, final, direction)["x"]
    two = lens.direct_logit_attribution(model, {"x": 2 * comps["attn.1"]}, final, direction)["x"]
    torch.testing.assert_close(two, 2 * one, atol=1e-5, rtol=1e-5, msg="thang LayerNorm lấy từ final_resid, cố định")
