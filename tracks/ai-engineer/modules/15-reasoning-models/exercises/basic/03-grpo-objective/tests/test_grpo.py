import math

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def g():
    return ex.module("grpo.py")


# ---------- Advantage theo nhóm ----------

def test_group_advantages_hand_example(g):
    rewards = torch.tensor([1.0, 0.0, 0.0, 1.0, 1.2, 1.2, 0.2, 0.2])
    adv = g.group_advantages(rewards, group_size=4)
    # nhóm 1: mean 0.5, std (Bessel) = sqrt(1/3); nhóm 2: mean 0.7, std = sqrt(1/3)
    s = math.sqrt(1 / 3) + 1e-4
    expected = torch.tensor([0.5, -0.5, -0.5, 0.5, 0.5, 0.5, -0.5, -0.5]) / s
    torch.testing.assert_close(adv, expected, rtol=1e-5, atol=1e-6)
    assert adv.shape == rewards.shape


def test_groups_are_independent(g):
    a = g.group_advantages(torch.tensor([0.0, 1.0, 10.0, 11.0]), group_size=2)
    torch.testing.assert_close(a[:2], a[2:], msg="mỗi nhóm so với trung bình của chính nó, không của cả batch")


def test_equal_rewards_give_zero_not_nan(g):
    adv = g.group_advantages(torch.tensor([1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]), group_size=3)
    assert torch.isfinite(adv).all()
    assert torch.all(adv[:6] == 0), "nhóm mọi lời giải cùng reward không có tín hiệu học"
    assert adv[7] > 0 > adv[6]


def test_scale_false_and_eps(g):
    rewards = torch.tensor([2.0, 0.0, 1.0, 1.0])
    torch.testing.assert_close(g.group_advantages(rewards, 2, scale=False), torch.tensor([1.0, -1.0, 0.0, 0.0]))
    small = g.group_advantages(torch.tensor([0.0, 1.0]), 2, eps=1e-4)
    big = g.group_advantages(torch.tensor([0.0, 1.0]), 2, eps=1.0)
    assert big[1] < small[1], "tham số eps phải được dùng"


def test_group_advantages_rejects_bad_shapes(g):
    with pytest.raises(ValueError):
        g.group_advantages(torch.ones(6), group_size=4)
    with pytest.raises(ValueError):
        g.group_advantages(torch.ones(4), group_size=1)


# ---------- KL k3 ----------

def test_k3_zero_and_nonnegative(g):
    x = torch.randn(1000, dtype=torch.float64)
    torch.testing.assert_close(g.kl_k3(x, x), torch.zeros_like(x))
    y = torch.randn(1000, dtype=torch.float64) * 3
    assert (g.kl_k3(x, y) >= 0).all(), "k3 không âm ở từng token, khác ước lượng thô log p - log p_ref"


def test_k3_is_unbiased_for_kl_policy_vs_ref(g):
    torch.manual_seed(0)
    p = torch.tensor([0.9, 0.09, 0.01], dtype=torch.float64)
    q = torch.tensor([0.1, 0.3, 0.6], dtype=torch.float64)
    kl_pq = float((p * (p / q).log()).sum())
    kl_qp = float((q * (q / p).log()).sum())
    tokens = torch.multinomial(p, 400_000, replacement=True)
    est = float(g.kl_k3(p.log()[tokens], q.log()[tokens]).mean())
    assert est == pytest.approx(kl_pq, rel=0.03), "token lấy mẫu từ policy: ước lượng KL(policy || ref)"
    assert abs(est - kl_qp) > 0.5, "không phải KL(ref || policy)"


# ---------- Clipped objective ----------

@pytest.mark.parametrize("ratio, adv, expected", [
    (1.5, 1.0, 1.2), (1.1, 1.0, 1.1), (0.5, 1.0, 0.5),
    (0.5, -1.0, -0.8), (0.9, -1.0, -0.9), (1.5, -1.0, -1.5),
])
def test_clipped_surrogate_table(g, ratio, adv, expected):
    old = torch.tensor([[-1.0]])
    new = old + math.log(ratio)
    out = g.clipped_surrogate(new, old, torch.tensor([adv]))
    assert out.shape == (1, 1)
    assert out.item() == pytest.approx(expected, rel=1e-5)


@pytest.mark.parametrize("ratio, adv, has_grad", [
    (1.5, 1.0, False), (1.1, 1.0, True), (0.5, 1.0, True),
    (0.5, -1.0, False), (0.9, -1.0, True), (1.5, -1.0, True),
])
def test_clip_only_stops_gradient_in_the_greedy_direction(g, ratio, adv, has_grad):
    old = torch.tensor([[-1.0]])
    new = (old + math.log(ratio)).clone().requires_grad_(True)
    g.clipped_surrogate(new, old, torch.tensor([adv])).sum().backward()
    assert (new.grad.abs().item() > 1e-6) == has_grad


def test_asymmetric_clip(g):
    old = torch.zeros(1, 2)
    new = torch.log(torch.tensor([[1.25, 1.35]]))
    out = g.clipped_surrogate(new, old, torch.tensor([1.0]), eps_low=0.2, eps_high=0.28)
    torch.testing.assert_close(out, torch.tensor([[1.25, 1.28]]))
    low = g.clipped_surrogate(torch.log(torch.tensor([[0.7]])), torch.zeros(1, 1), torch.tensor([-1.0]),
                              eps_low=0.2, eps_high=0.28)
    assert low.item() == pytest.approx(-0.8)


# ---------- Loss đầy đủ ----------

def _batch():
    torch.manual_seed(1)
    logp = -torch.rand(3, 5) * 2
    old = logp + 0.3 * torch.randn(3, 5)
    ref = logp + 0.5 * torch.randn(3, 5)
    mask = torch.tensor([[1, 1, 1, 1, 1], [1, 1, 0, 0, 0], [1, 1, 1, 0, 0]], dtype=torch.float32)
    adv = torch.tensor([1.0, -0.5, 0.25])
    return logp, old, ref, adv, mask


def _manual(logp, old, ref, adv, mask, beta, agg):
    rows, tokens = [], []
    for b in range(len(logp)):
        vals = []
        for t in range(len(logp[0])):
            if mask[b][t]:
                r = math.exp(logp[b][t] - old[b][t])
                surr = min(r * adv[b], min(max(r, 0.8), 1.2) * adv[b])
                d = ref[b][t] - logp[b][t]
                vals.append(-surr + beta * (math.exp(d) - d - 1))
        rows.append(sum(vals) / len(vals))
        tokens += vals
    return sum(rows) / len(rows) if agg == "sequence" else sum(tokens) / len(tokens)


@pytest.mark.parametrize("agg", ["sequence", "token"])
@pytest.mark.parametrize("beta", [0.0, 0.04])
def test_grpo_loss_matches_manual(g, agg, beta):
    logp, old, ref, adv, mask = _batch()
    loss, _ = g.grpo_loss(logp, old, ref, adv, mask, beta=beta, aggregation=agg)
    assert loss.item() == pytest.approx(_manual(logp.tolist(), old.tolist(), ref.tolist(), adv.tolist(),
                                                mask.tolist(), beta, agg), rel=1e-5)


def test_aggregations_differ_when_lengths_differ(g):
    logp, old, ref, adv, mask = _batch()
    seq, _ = g.grpo_loss(logp, old, ref, adv, mask, aggregation="sequence")
    tok, _ = g.grpo_loss(logp, old, ref, adv, mask, aggregation="token")
    assert abs(seq.item() - tok.item()) > 1e-3
    with pytest.raises(ValueError):
        g.grpo_loss(logp, old, ref, adv, mask, aggregation="mean")


def test_masked_positions_are_ignored(g):
    logp, old, ref, adv, mask = _batch()
    base, base_stats = g.grpo_loss(logp, old, ref, adv, mask)
    junk = mask == 0
    logp2, old2, ref2 = logp.clone(), old.clone(), ref.clone()
    logp2[junk], old2[junk], ref2[junk] = 5.0, -30.0, 20.0
    loss, stats = g.grpo_loss(logp2, old2, ref2, adv, mask)
    assert loss.item() == pytest.approx(base.item(), rel=1e-6)
    assert stats["kl"] == pytest.approx(base_stats["kl"], rel=1e-6)
    assert stats["clip_frac"] == pytest.approx(base_stats["clip_frac"])


def test_beta_zero_needs_no_reference(g):
    logp, old, ref, adv, mask = _batch()
    a, stats = g.grpo_loss(logp, old, None, adv, mask, beta=0.0)
    b, _ = g.grpo_loss(logp, old, ref, adv, mask, beta=0.0)
    assert a.item() == pytest.approx(b.item())
    assert stats["kl"] == 0.0


def test_on_policy_gradient_is_minus_advantage_over_length(g):
    logp, _, _, adv, mask = _batch()
    x = logp.clone().requires_grad_(True)
    loss, stats = g.grpo_loss(x, logp.detach(), None, adv, mask, beta=0.0, aggregation="sequence")
    loss.backward()
    lengths = mask.sum(-1, keepdim=True)
    expected = -adv.unsqueeze(-1) * mask / lengths / 3
    torch.testing.assert_close(x.grad, expected, rtol=1e-5, atol=1e-7)
    assert stats["clip_frac"] == 0.0


def test_stats(g):
    old = torch.zeros(2, 3)
    logp = torch.log(torch.tensor([[1.5, 1.0, 0.5], [1.5, 1.0, 0.5]]))
    ref = torch.zeros(2, 3)
    mask = torch.tensor([[1.0, 1.0, 1.0], [1.0, 1.0, 0.0]])
    _, stats = g.grpo_loss(logp, old, ref, torch.tensor([1.0, -1.0]), mask, beta=0.1)
    # chuỗi 1 (A > 0): token 1 bị cắt ở trên; chuỗi 2 (A < 0): token 3 bị cắt ở dưới nhưng nằm ngoài mask
    assert stats["clip_frac"] == pytest.approx(1 / 5)
    kl = [math.exp(-math.log(r)) + math.log(r) - 1 for r in (1.5, 1.0, 0.5, 1.5, 1.0)]
    assert stats["kl"] == pytest.approx(sum(kl) / 5, rel=1e-5)
    assert isinstance(stats["kl"], float) and isinstance(stats["clip_frac"], float)
