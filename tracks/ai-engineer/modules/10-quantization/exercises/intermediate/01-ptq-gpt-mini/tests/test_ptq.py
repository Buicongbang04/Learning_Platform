import importlib.util
import sys

import pytest
import torch
import torch.nn as nn

from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ptq.ipynb")


@pytest.fixture(scope="module")
def gpt_mini():
    path = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"
    spec = importlib.util.spec_from_file_location("m10_test_gpt_mini", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tiny_gpt(gpt_mini, seed=0):
    torch.manual_seed(seed)
    model = gpt_mini.GPT(gpt_mini.GPTConfig(vocab_size=50, block_size=16, n_layer=2, n_head=2, n_embd=32))
    with torch.no_grad():
        for p in model.parameters():
            p.add_(torch.randn_like(p) * 0.05)
    return model.eval()


def test_per_tensor_symmetric_values(nb):
    w = torch.tensor([[1.75, -0.875, 0.125, 0.0], [0.5, 0.375, -0.25, 0.0]])
    out = nb.fake_quantize_weight(w, 4, "tensor")
    assert out.shape == w.shape and out.dtype == w.dtype
    torch.testing.assert_close(out, torch.tensor([[1.75, -1.0, 0.0, 0.0], [0.5, 0.5, -0.25, 0.0]]))


def test_channel_and_group_scales(nb):
    w = torch.tensor([[1.75, -0.875, 0.125, 0.0], [0.5, 0.375, -0.25, 0.0]])
    s1 = torch.tensor(0.5 / 7)
    row1 = torch.round(w[1] / s1) * s1
    torch.testing.assert_close(nb.fake_quantize_weight(w, 4, "channel"), torch.stack([torch.tensor([1.75, -1.0, 0.0, 0.0]), row1]))
    g = nb.fake_quantize_weight(w, 4, 2)
    torch.testing.assert_close(g[0], torch.tensor([1.75, -1.0, 0.125, 0.0]))
    w2 = torch.tensor([[1.0, 0.3, 0.05, 0.01]])
    torch.testing.assert_close(nb.fake_quantize_weight(w2, 2, 2), torch.tensor([[1.0, 0.0, 0.05, 0.0]]))
    with pytest.raises(ValueError):
        nb.fake_quantize_weight(torch.randn(3, 10), 4, 4)


def test_asymmetric_uses_all_codes(nb):
    torch.manual_seed(0)
    w = torch.rand(8, 64) + 0.1
    sym = nb.fake_quantize_weight(w, 2, "channel", symmetric=True)
    asym = nb.fake_quantize_weight(w, 2, "channel", symmetric=False)
    assert sym.unique(dim=None).numel() <= 8 * 2 + 1
    assert all(asym[r].unique().numel() >= 3 for r in range(8)), "zero-point 2 bit phải dùng được hơn 2 mức trên dữ liệu dương"
    assert ((asym - w) ** 2).mean() < ((sym - w) ** 2).mean()
    exact = nb.fake_quantize_weight(torch.tensor([[-1.5, 0.0, 0.7, 253.5]]), 8, "channel", symmetric=False)
    torch.testing.assert_close(exact, torch.tensor([[-2.0, 0.0, 1.0, 253.0]])), "scale 1, zero-point làm tròn thành 2, mã kẹp ở 255"
    pos_vals = nb.fake_quantize_weight(torch.tensor([[2.0, 8.0]]), 4, "tensor", symmetric=False)
    torch.testing.assert_close(pos_vals, torch.tensor([[torch.round(torch.tensor(2.0 * 15 / 8)).item() * 8 / 15, 8.0]])), "khoảng chứa 0"
    z = nb.fake_quantize_weight(torch.zeros(2, 4), 4, "channel", symmetric=False)
    assert torch.equal(z, torch.zeros(2, 4))


def test_finer_granularity_lower_error(nb):
    torch.manual_seed(1)
    w = torch.randn(32, 128) * torch.exp(torch.randn(32, 1)) * torch.exp(0.5 * torch.randn(1, 128))
    errs = [((nb.fake_quantize_weight(w, 4, g) - w) ** 2).mean().item() for g in ("tensor", "channel", 32)]
    assert errs[0] > errs[1] > errs[2]


def test_quantize_model_copies_and_keeps_tie(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    before = {k: v.clone() for k, v in model.state_dict().items()}
    q = nb.quantize_model(model, 4, "channel")
    assert q is not model
    for k, v in model.state_dict().items():
        assert torch.equal(v, before[k]), "model gốc không được đổi"
    assert q.lm_head.weight is q.tok_emb.weight, "phải giữ weight tying trong bản sao"
    assert torch.equal(q.tok_emb.weight, model.tok_emb.weight), "mặc định không quantize embedding / lm_head dùng chung"
    assert torch.equal(q.pos_emb.weight, model.pos_emb.weight)
    for i in range(2):
        b, bq = model.blocks[i], q.blocks[i]
        for name in ("attn.qkv", "attn.proj", "mlp.fc", "mlp.proj"):
            lin, linq = b.get_submodule(name), bq.get_submodule(name)
            torch.testing.assert_close(linq.weight, nb.fake_quantize_weight(lin.weight, 4, "channel"))
            assert torch.equal(linq.bias, lin.bias), "bias giữ nguyên"
        assert torch.equal(bq.ln1.weight, b.ln1.weight)


def test_quantize_model_with_embedding(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    q = nb.quantize_model(model, 4, "channel", include_embedding=True)
    assert q.lm_head.weight is q.tok_emb.weight
    torch.testing.assert_close(q.tok_emb.weight, nb.fake_quantize_weight(model.tok_emb.weight, 4, "channel"))
    q8 = nb.quantize_model(model, 8, "channel")
    x = torch.randint(0, 50, (2, 16))
    torch.testing.assert_close(q8(x)[0], model(x)[0], atol=0.05, rtol=0.05)


def test_weight_storage_bytes(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    total_params = sum(p.numel() for p in model.parameters())
    lin_params = 2 * (32 * 96 + 32 * 32 + 32 * 128 + 128 * 32)
    rows = 2 * (96 + 32 + 128 + 32)
    other = total_params - lin_params
    assert nb.weight_storage_bytes(model, 4, "channel") == pytest.approx(lin_params / 2 + rows * 2 + other * 4)
    assert nb.weight_storage_bytes(model, 8, "tensor") == pytest.approx(lin_params + 8 * 2 + other * 4)
    assert nb.weight_storage_bytes(model, 4, 16, symmetric=False) == pytest.approx(lin_params / 2 + lin_params / 16 * 3 + other * 4)
    emb = 50 * 32
    assert nb.weight_storage_bytes(model, 4, "channel", include_embedding=True) == pytest.approx(
        (lin_params + emb) / 2 + (rows + 50) * 2 + (other - emb) * 4
    ), "embedding dùng chung đếm một lần"


def test_layer_sensitivity(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    before = {k: v.clone() for k, v in model.state_dict().items()}
    calls = []

    def eval_fn(m):
        calls.append(1)
        return float(sum(p.detach().abs().sum() for p in m.parameters()))

    names = ["blocks.1.mlp.fc", "blocks.0.attn.qkv"]
    out = nb.layer_sensitivity(model, names, torch.zeros_like, eval_fn)
    assert list(out) == names
    assert len(calls) == 3, "đo model gốc một lần, mỗi lớp một lần"
    for n in names:
        assert out[n] == pytest.approx(-float(model.get_submodule(n).weight.detach().abs().sum()), rel=1e-5), "chỉ thay đúng một lớp"
    for k, v in model.state_dict().items():
        assert torch.equal(v, before[k])
