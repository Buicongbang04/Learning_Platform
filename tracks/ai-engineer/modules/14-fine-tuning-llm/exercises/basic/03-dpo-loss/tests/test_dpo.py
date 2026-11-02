import copy
import math

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def dpo():
    return ex.module("dpo.py")


def manual_logps(logits, labels):
    out = []
    for b in range(logits.shape[0]):
        total = 0.0
        for t in range(1, logits.shape[1]):
            if labels[b, t] != -100:
                total += torch.log_softmax(logits[b, t - 1].double(), -1)[labels[b, t]].item()
        out.append(total)
    return torch.tensor(out, dtype=torch.float64)


def test_sequence_logps_matches_manual(dpo):
    torch.manual_seed(0)
    logits = torch.randn(3, 7, 11)
    labels = torch.randint(0, 11, (3, 7))
    labels[0, :3] = -100
    labels[1, :] = -100
    labels[1, 5] = 4
    labels[2, 6] = -100
    out = dpo.sequence_logps(logits, labels)
    assert out.shape == (3,)
    torch.testing.assert_close(out.double(), manual_logps(logits, labels), rtol=1e-5, atol=1e-5)


def test_sequence_logps_ignores_masked_positions(dpo):
    torch.manual_seed(1)
    logits = torch.randn(1, 6, 9)
    labels = torch.tensor([[-100, -100, -100, 2, 5, -100]])
    base = dpo.sequence_logps(logits, labels)
    noisy = logits.clone()
    noisy[0, :2] += 5 * torch.randn(2, 9)
    noisy[0, 5] += 5 * torch.randn(9)
    torch.testing.assert_close(dpo.sequence_logps(noisy, labels), base,
                               msg="logits ở vị trí không dự đoán token có label không được ảnh hưởng")
    assert dpo.sequence_logps(logits, torch.full((1, 6), -100)).item() == 0.0


def test_loss_is_log2_when_policy_equals_reference(dpo):
    p = torch.tensor([-12.0, -30.0, -5.5])
    r = torch.tensor([-14.0, -29.0, -7.0])
    loss, cr, rr = dpo.dpo_loss(p, r, p.clone(), r.clone(), beta=0.1)
    assert loss.item() == pytest.approx(math.log(2), abs=1e-6)
    assert torch.all(cr == 0) and torch.all(rr == 0)


def test_loss_value_and_beta(dpo):
    pc, pr = torch.tensor([-10.0, -20.0]), torch.tensor([-15.0, -18.0])
    rc, rr = torch.tensor([-12.0, -21.0]), torch.tensor([-14.0, -17.0])
    for beta in (0.1, 0.5):
        z = beta * ((pc - rc) - (pr - rr))
        expected = torch.log1p(torch.exp(-z)).mean().item()
        loss, chosen, rejected = dpo.dpo_loss(pc, pr, rc, rr, beta=beta)
        assert loss.item() == pytest.approx(expected, rel=1e-6)
        torch.testing.assert_close(chosen, beta * (pc - rc))
        torch.testing.assert_close(rejected, beta * (pr - rr))


def test_loss_sign_and_reference_matter(dpo):
    pc, pr = torch.tensor([-10.0]), torch.tensor([-10.0])
    rc, rr = torch.tensor([-13.0]), torch.tensor([-8.0])
    good, _, _ = dpo.dpo_loss(pc, pr, rc, rr, beta=0.2)
    bad, _, _ = dpo.dpo_loss(pr, pc, rr, rc, beta=0.2)
    assert good.item() < math.log(2) < bad.item(), "policy nâng chosen so với reference thì loss dưới log 2"
    ignore_ref, _, _ = dpo.dpo_loss(pc, pr, torch.zeros(1), torch.zeros(1), beta=0.2)
    assert ignore_ref.item() == pytest.approx(math.log(2), abs=1e-6), "cùng log p mà reference khác thì loss khác"


def test_gradient_pushes_chosen_up_rejected_down(dpo):
    pc = torch.tensor([-10.0, -9.0], requires_grad=True)
    pr = torch.tensor([-11.0, -8.0], requires_grad=True)
    loss, chosen, rejected = dpo.dpo_loss(pc, pr, torch.tensor([-10.5, -9.0]), torch.tensor([-10.0, -9.0]), 0.1)
    loss.backward()
    assert torch.all(pc.grad < 0) and torch.all(pr.grad > 0)
    assert not chosen.requires_grad and not rejected.requires_grad, "reward trả về để log, không mang gradient"


def tiny_model():
    from transformers import Qwen2Config, Qwen2ForCausalLM

    torch.manual_seed(0)
    return Qwen2ForCausalLM(Qwen2Config(vocab_size=50, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                                        num_attention_heads=4, num_key_value_heads=2))


def pref_batch():
    g = torch.Generator().manual_seed(0)
    prompt = torch.randint(0, 50, (4, 6), generator=g)
    chosen = torch.cat([prompt, torch.randint(0, 50, (4, 4), generator=g)], 1)
    rejected = torch.cat([prompt, torch.randint(0, 50, (4, 4), generator=g)], 1)
    labels_c, labels_r = chosen.clone(), rejected.clone()
    labels_c[:, :6] = -100
    labels_r[:, :6] = -100
    ones = torch.ones_like(chosen)
    return {"chosen_input_ids": chosen, "chosen_attention_mask": ones, "chosen_labels": labels_c,
            "rejected_input_ids": rejected, "rejected_attention_mask": ones, "rejected_labels": labels_r}


def test_dpo_step_trains_policy_keeps_reference_frozen(dpo):
    policy = tiny_model().train()
    reference = copy.deepcopy(policy).eval()
    ref_state = {k: v.clone() for k, v in reference.state_dict().items()}
    opt = torch.optim.AdamW(policy.parameters(), lr=5e-3)
    batch = pref_batch()
    history = [dpo.dpo_step(policy, reference, batch, beta=0.5, optimizer=opt) for _ in range(12)]
    assert set(history[0]) >= {"loss", "reward_margin", "reward_accuracy"}
    assert all(isinstance(h["loss"], float) for h in history)
    assert history[0]["loss"] == pytest.approx(math.log(2), abs=1e-4), "bước đầu policy trùng reference: loss = log 2"
    assert history[-1]["loss"] < 0.3 and history[-1]["reward_accuracy"] == 1.0
    assert history[-1]["reward_margin"] > history[0]["reward_margin"]
    for k, v in reference.state_dict().items():
        assert torch.equal(v, ref_state[k]), f"reference model bị đổi ở {k}"
    assert all(p.grad is None for p in reference.parameters()), "reference không được nhận gradient"
    policy.eval()
    with torch.no_grad():
        lp = {k: dpo.sequence_logps(m(batch[f"{k}_input_ids"]).logits, batch[f"{k}_labels"])
              for k in ("chosen", "rejected") for m in [policy]}
        lr = {k: dpo.sequence_logps(reference(batch[f"{k}_input_ids"]).logits, batch[f"{k}_labels"])
              for k in ("chosen", "rejected")}
    assert torch.all((lp["chosen"] - lr["chosen"]) > (lp["rejected"] - lr["rejected"])), (
        "sau train, log-ratio so với reference của chosen cao hơn của rejected")
