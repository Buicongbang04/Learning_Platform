import importlib.util
import math
import sys

import numpy as np
import pytest
import torch
import torch.nn.functional as F
from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)
GPT_FILE = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("inside_gpt2.ipynb")


@pytest.fixture(scope="module")
def G():
    spec = importlib.util.spec_from_file_location("m08_i01_gpt", GPT_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hf_tiny():
    """GPT-2 tí hon khởi tạo ngẫu nhiên bằng transformers: không tải gì từ mạng."""
    from transformers import GPT2Config, GPT2LMHeadModel

    torch.manual_seed(0)
    cfg = GPT2Config(vocab_size=61, n_positions=20, n_embd=24, n_layer=2, n_head=4, resid_pdrop=0.0, embd_pdrop=0.0, attn_pdrop=0.0)
    model = GPT2LMHeadModel(cfg).eval()
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith("bias") or "ln_" in name:
                p.add_(torch.randn_like(p) * 0.3)
            if "c_fc.weight" in name:
                p.mul_(50)
            if "mlp.c_proj.weight" in name:
                p.mul_(25)
            if "wte" in name:
                p.mul_(50)
    return model


def tiny(G, seed=0):
    torch.manual_seed(seed)
    model = G.GPT(G.GPTConfig(vocab_size=30, block_size=16, n_layer=2, n_head=3, n_embd=12)).eval()
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith("bias"):
                p.add_(torch.randn_like(p) * 0.3)
    return model


def all_hooks(model):
    return sum(len(m._forward_hooks) + len(m._forward_pre_hooks) for m in model.modules())


def test_gpt2_conversion_matches_transformers(nb, G, hf_tiny):
    model = nb.gpt2_into_gpt_mini(G, hf_tiny)
    assert isinstance(model, G.GPT) and not model.training
    assert model.config.block_size == 20 and model.config.n_layer == 2 and model.config.n_head == 4
    assert model.lm_head.weight is model.tok_emb.weight, "giữ weight tying"
    idx = torch.randint(61, (2, 11), generator=torch.Generator().manual_seed(1))
    with torch.no_grad():
        ref = hf_tiny(idx).logits
        out, _ = model(idx)
    torch.testing.assert_close(out, ref, atol=2e-5, rtol=1e-4, msg="logits phải khớp GPT2LMHeadModel")


def test_ablate_zero_all_heads_leaves_only_bias(nb, G):
    model = tiny(G)
    idx = torch.randint(30, (2, 7), generator=torch.Generator().manual_seed(2))
    seen = {}
    handle = model.blocks[1].attn.register_forward_hook(lambda m, a, o: seen.__setitem__("out", o.detach()))
    with nb.ablate_heads(model, [(1, 0), (1, 1), (1, 2)]):
        with torch.no_grad():
            model(idx)
    handle.remove()
    bias = model.blocks[1].attn.proj.bias.detach()
    torch.testing.assert_close(seen["out"], bias.expand(2, 7, 12), msg="zero ablation mọi head: chỉ còn bias của proj")
    assert all_hooks(model) == 0


def test_ablate_mean_replaces_only_chosen_head(nb, G):
    model = tiny(G)
    idx = torch.randint(30, (2, 7), generator=torch.Generator().manual_seed(3))
    z = {}
    handle = model.blocks[0].attn.proj.register_forward_pre_hook(lambda m, a: z.__setitem__("z", a[0].detach().clone()))
    with torch.no_grad():
        model(idx)
    handle.remove()
    means = {0: torch.randn(3, 4), 1: torch.randn(3, 4)}
    expected = z["z"].view(2, 7, 3, 4).clone()
    expected[:, :, 1] = means[0][1]
    expected = model.blocks[0].attn.proj(expected.view(2, 7, 12)).detach()
    seen = {}
    handle = model.blocks[0].attn.register_forward_hook(lambda m, a, o: seen.__setitem__("out", o.detach()))
    with nb.ablate_heads(model, [(0, 1)], means):
        with torch.no_grad():
            model(idx)
    handle.remove()
    torch.testing.assert_close(seen["out"], expected, atol=1e-6, rtol=1e-5)


def test_ablate_restores_model_even_on_error(nb, G):
    model = tiny(G)
    idx = torch.randint(30, (1, 5), generator=torch.Generator().manual_seed(4))
    with torch.no_grad():
        before, _ = model(idx)
    with pytest.raises(RuntimeError):
        with nb.ablate_heads(model, [(0, 0), (1, 2)]):
            raise RuntimeError("lỗi giữa chừng")
    assert all_hooks(model) == 0, "gỡ hook kể cả khi có exception"
    with torch.no_grad():
        after, _ = model(idx)
    torch.testing.assert_close(after, before)


class OracleModel:
    """Model giả: đoán đúng (logit 20) token kế tiếp chỉ ở các vị trí trong `good`, còn lại logits bằng 0."""

    def __init__(self, seq, good, vocab):
        self.seq, self.good, self.vocab = seq, set(good), vocab

    def __call__(self, idx):
        B, T = idx.shape
        logits = torch.zeros(B, T, self.vocab)
        for p in range(T - 1):
            if p in self.good:
                logits[torch.arange(B), p, idx[:, p + 1]] = 20.0
        return logits, None


@pytest.mark.parametrize("prefix", [0, 1])
def test_in_context_loss_positions(nb, prefix):
    half, V = 6, 50
    r = torch.randint(V, (3, half), generator=torch.Generator().manual_seed(5))
    seq = torch.cat([torch.full((3, prefix), 7), r, r], dim=1).long()
    s1, s2 = prefix, prefix + half
    first_preds = range(s1, s1 + half - 1)
    second_preds = range(s2, s2 + half - 1)
    lv = math.log(V)
    good_first = OracleModel(seq, first_preds, V)
    a, b = nb.in_context_loss(good_first, seq, half)
    assert a < 1e-3 and b == pytest.approx(lv, rel=1e-4), "bản 1: dự đoán token thứ 2..half của bản 1"
    good_second = OracleModel(seq, second_preds, V)
    a, b = nb.in_context_loss(good_second, seq, half)
    assert a == pytest.approx(lv, rel=1e-4) and b < 1e-3, "bản 2: dự đoán token thứ 2..half của bản 2"
    assert isinstance(a, float) and isinstance(b, float)


def test_repeated_token_labels(nb):
    idx = torch.tensor([[50, 3, 4, 3, 3, 50, 4], [9, 9, 1, 2, 1, 9, 0]])
    out = nb.repeated_token_labels(idx)
    assert isinstance(out, np.ndarray) and out.dtype == np.int64
    assert out.tolist() == [[0, 0, 0, 1, 1, 0, 1], [0, 0, 0, 0, 1, 1, 0]]


def test_lens_metrics(nb):
    g = torch.Generator().manual_seed(6)
    final = torch.randn(2, 5, 11, generator=g)
    targets = torch.randint(11, (2, 5), generator=g)
    same = nb.lens_metrics(final, final, targets)
    assert same["top1_agree"] == 1.0 and abs(same["kl"]) < 1e-6
    assert same["ce"] == pytest.approx(F.cross_entropy(final.reshape(-1, 11), targets.reshape(-1)).item(), rel=1e-5)
    lens = torch.zeros(1, 1, 3)
    fin = torch.tensor([[[math.log(3.0), 0.0, 0.0]]])
    m = nb.lens_metrics(lens, fin, torch.tensor([[1]]))
    p = torch.tensor([0.6, 0.2, 0.2])
    assert m["kl"] == pytest.approx(float((p * (p / (1 / 3)).log()).sum()), rel=1e-4), "KL(p_model || p_lens)"
    assert m["ce"] == pytest.approx(math.log(3), rel=1e-5)
    assert m["top1_agree"] == 1.0
    other = nb.lens_metrics(torch.tensor([[[0.0, 1.0, 0.0]]]), fin, torch.tensor([[1]]))
    assert other["top1_agree"] == 0.0
    assert all(isinstance(v, float) for v in m.values())
