import math

import numpy as np
import pytest
import torch
import torch.nn as nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("pg.ipynb")


@pytest.fixture(scope="module")
def envs_mod():
    gym = pytest.importorskip("gymnasium")
    from gymnasium import spaces

    class ContextBandit(gym.Env):
        """Mỗi episode một bước: observation one-hot của ngữ cảnh 0/1, reward 1 nếu action trùng ngữ cảnh."""

        observation_space = spaces.Box(0.0, 1.0, (2,), np.float32)
        action_space = spaces.Discrete(2)

        def reset(self, seed=None, options=None):
            super().reset(seed=seed)
            self.ctx = int(self.np_random.integers(2))
            return np.eye(2, dtype=np.float32)[self.ctx], {}

        def step(self, action):
            return np.eye(2, dtype=np.float32)[self.ctx], float(action == self.ctx), True, False, {}

    class Counter(gym.Env):
        """observation = [số bước đã đi], reward 1 mỗi bước, không bao giờ terminated, bị cắt sau 3 bước."""

        observation_space = spaces.Box(0.0, 10.0, (1,), np.float32)
        action_space = spaces.Discrete(2)

        def reset(self, seed=None, options=None):
            super().reset(seed=seed)
            self.t = 0
            return np.array([0.0], dtype=np.float32), {}

        def step(self, action):
            self.t += 1
            return np.array([float(self.t)], dtype=np.float32), 1.0, False, self.t >= 3, {}

    return gym, ContextBandit, Counter


class FixedModel(nn.Module):
    """Policy cố định P(action 1) = 0.75; V(s) = 10 · obs[0]."""

    def dist(self, obs):
        return torch.distributions.Categorical(probs=torch.tensor([0.25, 0.75]).expand(len(obs), 2))

    def value(self, obs):
        return 10.0 * obs[:, 0]


def test_actor_critic(nb):
    torch.manual_seed(0)
    m = nb.ActorCritic(4, 3)
    obs = torch.randn(7, 4)
    assert m.dist(obs).logits.shape == (7, 3)
    assert m.value(obs).shape == (7,), "value trả (B,), không phải (B, 1)"
    n_actor = 4 * 64 + 64 + 64 * 64 + 64 + 64 * 3 + 3
    n_critic = 4 * 64 + 64 + 64 * 64 + 64 + 64 + 1
    assert sum(p.numel() for p in m.actor.parameters()) == n_actor
    assert sum(p.numel() for p in m.critic.parameters()) == n_critic
    assert m.dist(obs).entropy().mean().item() == pytest.approx(math.log(3), abs=0.01), "tầng cuối actor gain 0.01"


def test_reinforce_loss(nb):
    logp = torch.tensor([-0.5, -1.0, -2.0], requires_grad=True)
    G = torch.tensor([3.0, 1.0, -1.0])
    b = torch.tensor([1.0, 1.0, 1.0], requires_grad=True)
    loss = nb.reinforce_loss(logp, G, b)
    assert loss.item() == pytest.approx(-(-0.5 * 2 + -1.0 * 0 + -2.0 * -2) / 3)
    loss.backward()
    torch.testing.assert_close(logp.grad, -torch.tensor([2.0, 0.0, -2.0]) / 3)
    assert b.grad is None or torch.all(b.grad == 0), "không để gradient của policy loss chảy vào baseline"
    assert nb.reinforce_loss(logp.detach(), G).item() == pytest.approx(-(-0.5 * 3 + -1.0 * 1 + -2.0 * -1) / 3)


def test_ppo_policy_loss_values(nb):
    ratio = torch.tensor([0.5, 1.0, 1.5, 1.1, 0.5])
    new = ratio.log().requires_grad_()
    old = torch.zeros(5)
    adv = torch.tensor([1.0, -1.0, 1.0, -2.0, -1.0])
    loss, stats = nb.ppo_policy_loss(new, old, adv, 0.2)
    terms = [min(0.5, 0.8), -1.0, min(1.5, 1.2), -2.2, min(-0.5, -0.8)]
    assert loss.item() == pytest.approx(-sum(terms) / 5, rel=1e-6)
    assert isinstance(stats["clipfrac"], float) and stats["clipfrac"] == pytest.approx(3 / 5)
    kl = ((ratio - 1) - ratio.log()).mean().item()
    assert stats["approx_kl"] == pytest.approx(kl, rel=1e-5)
    loss.backward()
    g = new.grad
    assert g[2] == 0, "ρ = 1.5 > 1 + ε với A > 0: nhánh clip được chọn, không còn gradient"
    assert g[4] == 0, "ρ = 0.5 < 1 − ε với A < 0: nhánh clip được chọn, không còn gradient"
    assert g[0] == pytest.approx(-0.5 * 1.0 / 5), "ρ = 0.5 với A > 0: vẫn kéo xác suất lên (nhánh không clip là min)"
    assert g[1] == pytest.approx(1.0 / 5)


def test_gae_pasted(nb):
    adv, ret = nb.gae(np.array([1.0, 1.0]), np.array([0.5, 0.5]), np.array([2.0, 4.0]),
                      np.array([False, False]), np.array([True, False]), 0.9, 0.95)
    assert adv[0] == pytest.approx(1 + 0.9 * 2 - 0.5), "truncated: bootstrap, rồi cắt đệ quy"
    assert adv[1] == pytest.approx(1 + 0.9 * 4 - 0.5)
    np.testing.assert_allclose(ret, adv + 0.5)


def test_collect_rollout_counter(nb, envs_mod):
    gym, _, Counter = envs_mod
    envs = nb.make_vec_env(Counter, 2)
    obs, _ = envs.reset(seed=0)
    torch.manual_seed(0)
    buf, obs = nb.collect_rollout(envs, FixedModel(), obs, 4)
    assert buf["obs"].shape == (4, 2, 1) and buf["obs"].dtype == np.float32
    assert buf["actions"].shape == (4, 2) and buf["actions"].dtype == np.int64
    np.testing.assert_allclose(buf["obs"][:, 0, 0], [0, 1, 2, 0])
    np.testing.assert_allclose(buf["values"][:, 0], [0, 10, 20, 0])
    np.testing.assert_allclose(buf["next_values"][:, 0], [10, 20, 30, 10], err_msg=(
        "bước bị cắt: next_values là V của final_obs (30), không phải của observation sau reset (0)"))
    np.testing.assert_array_equal(buf["truncated"][:, 1], [False, False, True, False])
    assert not buf["terminated"].any()
    np.testing.assert_allclose(buf["rewards"], 1.0)
    assert buf["episode_returns"] == [3.0, 3.0]
    expected_logp = np.where(buf["actions"] == 1, math.log(0.75), math.log(0.25))
    np.testing.assert_allclose(buf["logp"], expected_logp, rtol=1e-6)
    np.testing.assert_allclose(obs[:, 0], [1, 1])
    buf2, obs = nb.collect_rollout(envs, FixedModel(), obs, 3)
    assert buf2["episode_returns"] == [3.0, 3.0], "return dở dang phải sống qua hai lần gọi"


def test_ppo_update_matches_reference(nb):
    torch.manual_seed(1)
    model = nb.ActorCritic(3, 2, hidden=8)
    ref = nb.ActorCritic(3, 2, hidden=8)
    ref.load_state_dict(model.state_dict())
    g = torch.Generator().manual_seed(1)
    B = 12
    batch = {"obs": torch.randn(B, 3, generator=g), "actions": torch.randint(0, 2, (B,), generator=g),
             "advantages": 5 + 3 * torch.randn(B, generator=g), "returns": torch.randn(B, generator=g)}
    with torch.no_grad():
        batch["logp"] = model.dist(batch["obs"]).log_prob(batch["actions"]) + 0.3 * torch.randn(B, generator=g)
    opt = torch.optim.SGD(model.parameters(), lr=0.1)
    stats = nb.ppo_update(model, opt, batch, np.random.default_rng(0), epochs=1, n_minibatches=1, clip_eps=0.2,
                          vf_coef=0.5, ent_coef=0.5, max_grad_norm=1e9)
    d = ref.dist(batch["obs"])
    adv = (batch["advantages"] - batch["advantages"].mean()) / (batch["advantages"].std() + 1e-8)
    ratio = (d.log_prob(batch["actions"]) - batch["logp"]).exp()
    pl = -torch.min(ratio * adv, ratio.clamp(0.8, 1.2) * adv).mean()
    vl = 0.5 * ((ref.value(batch["obs"]) - batch["returns"]) ** 2).mean()
    loss = pl + 0.5 * vl - 0.5 * d.entropy().mean()
    loss.backward()
    with torch.no_grad():
        for p, q in zip(model.parameters(), ref.parameters()):
            torch.testing.assert_close(p, q - 0.1 * q.grad, msg="một bước SGD phải khớp loss tham chiếu "
                                       "(advantage chuẩn hoá trong minibatch, value loss có 1/2, trừ entropy)")
    assert set(stats) >= {"clipfrac", "approx_kl", "entropy", "value_loss"}
    assert stats["value_loss"] == pytest.approx(vl.item(), rel=1e-5)

    before = [p.detach().clone() for p in model.parameters()]
    nb.ppo_update(model, opt, batch, np.random.default_rng(0), epochs=1, n_minibatches=1, max_grad_norm=0.01)
    change = torch.sqrt(sum(((p - q) ** 2).sum() for p, q in zip(model.parameters(), before)))
    assert change.item() <= 0.1 * 0.01 * 1.001, "clip norm gradient theo max_grad_norm trước bước optimizer"


def test_train_reinforce_discounted_returns(nb, envs_mod, monkeypatch):
    _, _, Counter = envs_mod
    seen = []
    real = nb.reinforce_loss

    def spy(logp, returns, baseline=None):
        seen.append(returns.detach().clone())
        return real(logp, returns, baseline)

    monkeypatch.setattr(nb, "reinforce_loss", spy)
    nb.train_reinforce(Counter, 6, seed=0, gamma=0.5, episodes_per_batch=2)
    assert len(seen) == 1
    torch.testing.assert_close(seen[0], torch.tensor([1.75, 1.5, 1.0, 1.75, 1.5, 1.0]),
                               msg="reward-to-go có chiết khấu từng episode, nối theo thứ tự episode")


def test_train_ppo_batch_and_lr(nb, envs_mod, monkeypatch):
    _, _, Counter = envs_mod
    batches, lrs = [], []
    real = nb.ppo_update

    def spy(model, opt, batch, rng, **kw):
        batches.append({k: v.clone() for k, v in batch.items()})
        lrs.append(opt.param_groups[0]["lr"])
        return real(model, opt, batch, rng, **kw)

    monkeypatch.setattr(nb, "ppo_update", spy)
    nb.train_ppo(Counter, 4 * 2 * 5, seed=0, n_envs=2, n_steps=5, lr=1e-3, gamma=0.9, lam=0.8)
    assert lrs == pytest.approx([1e-3, 7.5e-4, 5e-4, 2.5e-4]), "lr giảm tuyến tính, đặt ở đầu mỗi lần lặp"
    b = batches[0]
    assert b["obs"].shape == (10, 1) and b["actions"].dtype == torch.int64
    np.testing.assert_allclose(b["obs"][:, 0].numpy(), [0, 0, 1, 1, 2, 2, 0, 0, 1, 1]), "làm phẳng (T, N) theo thứ tự bước rồi env"
    assert not torch.allclose(b["returns"], b["advantages"]), "returns = advantages + values (mục tiêu của critic)"


def test_train_reinforce_learns_bandit(nb, envs_mod):
    _, ContextBandit, _ = envs_mod
    for baseline in [False, True]:
        h = nb.train_reinforce(ContextBandit, 3_000, seed=0, baseline=baseline, lr=1e-2, episodes_per_batch=16)
        assert len(h["returns"]) >= 3_000 and h["end_steps"][-1] == len(h["returns"])
        assert np.mean(h["returns"][-200:]) > 0.9, f"baseline={baseline}: phải học được action = ngữ cảnh"
    a = nb.train_reinforce(ContextBandit, 300, seed=3)
    b = nb.train_reinforce(ContextBandit, 300, seed=3)
    assert a["returns"] == b["returns"]


def test_train_ppo_learns_bandit(nb, envs_mod):
    _, ContextBandit, _ = envs_mod
    h = nb.train_ppo(ContextBandit, 4_096, seed=0, n_envs=4, n_steps=64, lr=3e-3)
    assert len(h["stats"]) == 16 and [s["step"] for s in h["stats"]][:2] == [256, 512]
    assert len(h["returns"]) == 4_096 and h["end_steps"][0] == 256 and h["end_steps"][-1] == 4_096
    assert np.mean(h["returns"][-512:]) > 0.9
    again = nb.train_ppo(ContextBandit, 512, seed=2, n_envs=2, n_steps=32)
    again2 = nb.train_ppo(ContextBandit, 512, seed=2, n_envs=2, n_steps=32)
    assert again["returns"] == again2["returns"]
    for p, q in zip(again["model"].parameters(), again2["model"].parameters()):
        assert torch.equal(p, q)
