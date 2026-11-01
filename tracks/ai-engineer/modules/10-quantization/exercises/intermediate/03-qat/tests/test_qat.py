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
    return ex.notebook("qat.ipynb")


@pytest.fixture(scope="module")
def gpt_mini():
    path = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"
    spec = importlib.util.spec_from_file_location("m10_test_gpt_mini_03", path)
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


def test_fake_quant_ste_forward(nb):
    w = torch.tensor([[1.75, -0.875, 0.125, 0.0], [0.5, 0.375, -0.25, 0.0]])
    out = nb.fake_quant_ste(w, 4, 2)
    s = torch.tensor([[0.25, 0.125 / 7], [0.5 / 7, 0.25 / 7]])
    ref = (torch.round(w.reshape(2, 2, 2) / s[..., None]) * s[..., None]).reshape(2, 4)
    torch.testing.assert_close(out, ref)
    assert torch.equal(nb.fake_quant_ste(torch.zeros(2, 4), 4, 2), torch.zeros(2, 4))
    with pytest.raises(ValueError):
        nb.fake_quant_ste(torch.randn(2, 6), 4, 4)


def test_fake_quant_ste_gradient_is_identity(nb):
    torch.manual_seed(0)
    w = torch.randn(4, 8, requires_grad=True)
    upstream = torch.randn(4, 8)
    (nb.fake_quant_ste(w, 3, 4) * upstream).sum().backward()
    torch.testing.assert_close(w.grad, upstream), "STE: gradient đi thẳng qua, kể cả ở phần tử lớn nhất (scale không nhận gradient)"


def test_qat_linear_shares_parameters(nb):
    torch.manual_seed(1)
    lin = nn.Linear(8, 3)
    q = nb.QATLinear(lin, 4, 4)
    assert q.weight is lin.weight and q.bias is lin.bias
    assert (q.in_features, q.out_features, q.bits, q.group_size) == (8, 3, 4, 4)
    x = torch.randn(5, 8)
    torch.testing.assert_close(q(x), x @ nb.fake_quant_ste(lin.weight, 4, 4).T + lin.bias)
    q(x).sum().backward()
    assert lin.weight.grad is not None and lin.weight.grad.abs().sum() > 0


def test_prepare_qat(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    q = nb.prepare_qat(model, 4, 16)
    assert q is not model
    assert sum(isinstance(m, nb.QATLinear) for m in q.modules()) == 8
    assert not any(isinstance(m, nb.QATLinear) for m in model.modules()), "model gốc không bị thay module"
    assert type(q.lm_head) is nn.Linear and q.lm_head.weight is q.tok_emb.weight
    assert sum(p.numel() for p in q.parameters()) == sum(p.numel() for p in model.parameters())
    assert not any(p is pm for p in q.parameters() for pm in model.parameters()), "bản sao không dùng chung tham số với gốc"


def test_prepare_then_train_updates_float_weights(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    q = nb.prepare_qat(model, 2, 16).train()
    torch.manual_seed(0)
    data = torch.arange(16).repeat(4, 1) % 50
    opt = torch.optim.AdamW(q.parameters(), lr=3e-3)
    losses = []
    for _ in range(40):
        _, loss = q(data[:, :-1], data[:, 1:])
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(loss.item())
    assert losses[-1] < 0.5 * losses[0], "model QAT phải học được qua STE"
    assert not torch.equal(q.blocks[0].attn.qkv.weight, model.blocks[0].attn.qkv.weight)


def test_convert_qat(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    q = nb.prepare_qat(model, 3, 16)
    c = nb.convert_qat(q)
    assert not any(isinstance(m, nb.QATLinear) for m in c.modules())
    assert sum(isinstance(m, nb.QATLinear) for m in q.modules()) == 8, "convert trả bản sao, không sửa model QAT"
    assert c.lm_head.weight is c.tok_emb.weight
    lin = c.blocks[1].mlp.fc
    assert type(lin) is nn.Linear
    torch.testing.assert_close(lin.weight, nb.fake_quant_ste(model.blocks[1].mlp.fc.weight, 3, 16))
    assert torch.equal(lin.bias, model.blocks[1].mlp.fc.bias)
    x = torch.randint(0, 50, (2, 16))
    with torch.no_grad():
        torch.testing.assert_close(c(x)[0], q(x)[0], atol=1e-5, rtol=1e-5)
    codes = c.blocks[0].attn.proj.weight.reshape(32, 2, 16)
    scale = codes.abs().amax(dim=-1, keepdim=True) / 3
    torch.testing.assert_close(codes / scale, torch.round(codes / scale), atol=1e-4, rtol=0)
