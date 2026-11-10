import math

import pytest
import torch
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def lora():
    return ex.module("lora.py")


def tiny_qwen():
    from transformers import Qwen2Config, Qwen2ForCausalLM

    torch.manual_seed(0)
    config = Qwen2Config(vocab_size=97, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                         num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64,
                         tie_word_embeddings=True)
    return Qwen2ForCausalLM(config).eval()


def layer(lora, r=4, alpha=8.0, dropout=0.0, bias=True, seed=0):
    torch.manual_seed(seed)
    return lora.LoRALinear(nn.Linear(24, 16, bias=bias), r=r, alpha=alpha, dropout=dropout)


def test_init_zero_b_random_a_same_output(lora):
    m = layer(lora)
    assert tuple(m.lora_A.shape) == (4, 24) and tuple(m.lora_B.shape) == (16, 4)
    assert torch.count_nonzero(m.lora_B) == 0, "B khởi tạo bằng 0"
    assert m.lora_A.abs().max() > 0 and m.lora_A.std() > 0.05, "A khởi tạo ngẫu nhiên, không phải 0"
    assert m.lora_A.abs().max() <= 1 / math.sqrt(24) + 1e-6, "A theo Kaiming đều a=sqrt(5): |A| <= 1/sqrt(in_features)"
    x = torch.randn(5, 24)
    assert torch.equal(m(x), m.base(x)), "lúc khởi tạo LoRA không đổi output của lớp gốc"


def test_first_backward_only_b_gets_gradient(lora):
    m = layer(lora)
    m(torch.randn(8, 24)).pow(2).sum().backward()
    assert m.lora_B.grad is not None and m.lora_B.grad.abs().sum() > 0
    assert m.lora_A.grad is not None and m.lora_A.grad.abs().sum() == 0, (
        "với B = 0, gradient của A ở bước đầu phải bằng đúng 0")


def test_base_frozen_only_lora_trainable(lora):
    m = layer(lora)
    assert not m.base.weight.requires_grad and not m.base.bias.requires_grad
    assert m.lora_A.requires_grad and m.lora_B.requires_grad
    before = m.base.weight.detach().clone()
    opt = torch.optim.SGD([p for p in m.parameters() if p.requires_grad], lr=0.1)
    for _ in range(3):
        opt.zero_grad()
        m(torch.randn(8, 24)).pow(2).sum().backward()
        opt.step()
    assert torch.equal(m.base.weight, before), "trọng số gốc không đổi khi train"
    assert m.lora_B.abs().sum() > 0


@pytest.mark.parametrize("r,alpha", [(4, 8.0), (8, 32.0), (2, 2.0)])
def test_scaling_alpha_over_r(lora, r, alpha):
    m = layer(lora, r=r, alpha=alpha)
    assert m.scaling == pytest.approx(alpha / r)
    torch.manual_seed(1)
    with torch.no_grad():
        m.lora_A.copy_(torch.randn_like(m.lora_A))
        m.lora_B.copy_(torch.randn_like(m.lora_B))
    x = torch.randn(3, 24)
    expected = m.base(x) + x @ ((alpha / r) * m.lora_B @ m.lora_A).T
    torch.testing.assert_close(m(x), expected, rtol=1e-5, atol=1e-5)
    torch.testing.assert_close(m.delta_weight(), (alpha / r) * m.lora_B @ m.lora_A, rtol=1e-6, atol=1e-6)


def test_merge_unmerge(lora):
    m = layer(lora, r=4, alpha=16.0)
    with torch.no_grad():
        m.lora_B.copy_(torch.randn_like(m.lora_B))
    x = torch.randn(6, 24)
    before = m(x)
    w0 = m.base.weight.detach().clone()
    m.merge()
    assert m.merged
    torch.testing.assert_close(m(x), before, rtol=1e-5, atol=1e-5)
    torch.testing.assert_close(m.base(x), before, rtol=1e-5, atol=1e-5, msg="sau merge, lớp gốc một mình cho cùng output")
    m.merge()
    torch.testing.assert_close(m(x), before, rtol=1e-5, atol=1e-5, msg="merge hai lần không được cộng hai lần")
    m.unmerge()
    assert not m.merged
    torch.testing.assert_close(m.base.weight, w0, rtol=0, atol=1e-6)
    torch.testing.assert_close(m(x), before, rtol=1e-5, atol=1e-5)
    m.unmerge()
    torch.testing.assert_close(m.base.weight, w0, rtol=0, atol=1e-6)


def test_dropout_only_on_lora_branch(lora):
    m = layer(lora, dropout=0.9).train()
    x = torch.randn(4, 24)
    torch.testing.assert_close(m(x), m.base(x), msg="B = 0: dropout chỉ áp lên nhánh LoRA, output vẫn bằng lớp gốc")
    with torch.no_grad():
        m.lora_B.copy_(torch.randn_like(m.lora_B))
    torch.manual_seed(0)
    a = m(x)
    torch.manual_seed(1)
    b = m(x)
    assert not torch.allclose(a, b), "train mode: dropout làm nhánh LoRA ngẫu nhiên"
    m.eval()
    assert torch.equal(m(x), m(x))


def test_inject_counts_and_identity(lora):
    model = tiny_qwen()
    ids = torch.randint(0, 97, (2, 10))
    with torch.no_grad():
        ref = model(ids).logits
    total_before = sum(p.numel() for p in model.parameters())
    names = lora.inject_lora(model, ["q_proj", "v_proj"], r=4, alpha=8.0)
    assert names == sorted(names) and len(names) == 4
    assert all(n.endswith(("q_proj", "v_proj")) for n in names)
    assert sum(isinstance(m, lora.LoRALinear) for m in model.modules()) == 4
    trainable, total = lora.count_parameters(model)
    expected = 2 * (4 * (32 + 32) + 4 * (32 + 16))
    assert trainable == expected, "q_proj 32→32, v_proj 32→16 (2 KV head × 8): r (in + out) mỗi lớp"
    assert total == total_before + expected
    assert all(not p.requires_grad for n, p in model.named_parameters() if "lora_" not in n), (
        "mọi tham số ngoài LoRA (embedding, norm, MLP...) phải đóng băng")
    with torch.no_grad():
        torch.testing.assert_close(model(ids).logits, ref)


def test_inject_matches_peft_trainable_count(lora):
    from peft import LoraConfig, get_peft_model

    ours = tiny_qwen()
    lora.inject_lora(ours, ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                     r=8, alpha=16.0)
    theirs = get_peft_model(tiny_qwen(), LoraConfig(
        r=8, lora_alpha=16, target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj",
                                            "down_proj"]))
    peft_trainable = sum(p.numel() for p in theirs.parameters() if p.requires_grad)
    assert lora.count_parameters(ours)[0] == peft_trainable


def test_inject_unknown_target_raises(lora):
    with pytest.raises(ValueError):
        lora.inject_lora(tiny_qwen(), ["not_a_layer"], r=4, alpha=8.0)


def test_train_then_merge_and_unload(lora):
    model = tiny_qwen()
    lora.inject_lora(model, ["q_proj", "v_proj", "down_proj"], r=4, alpha=8.0)
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-2)
    ids = torch.randint(0, 97, (4, 12))
    losses = []
    for _ in range(5):
        out = model(ids, labels=ids)
        opt.zero_grad()
        out.loss.backward()
        opt.step()
        losses.append(out.loss.item())
    assert losses[-1] < losses[0], "train được nhánh LoRA"
    model.eval()
    with torch.no_grad():
        trained = model(ids).logits
    merged = lora.merge_and_unload(model)
    assert not any(isinstance(m, lora.LoRALinear) for m in merged.modules())
    assert all(type(m.self_attn.q_proj) is nn.Linear for m in merged.model.layers)
    with torch.no_grad():
        torch.testing.assert_close(merged(ids).logits, trained, rtol=1e-4, atol=1e-4)
    assert sum(p.numel() for p in merged.parameters()) == sum(p.numel() for p in tiny_qwen().parameters())
