from types import SimpleNamespace

import numpy as np
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("dqn.ipynb")


class Corridor:
    """5 ô thẳng hàng, xuất phát ở ô 0, đích ở ô 4. Action 1 sang phải, 0 sang trái (tường ở ô 0).

    Observation one-hot 5 chiều. Reward +1 khi tới đích (terminated), -0.01 mỗi bước khác; bị cắt sau 30 bước.
    Policy tối ưu: luôn sang phải, 4 bước.
    """

    def __init__(self, limit: int = 30):
        self.limit = limit
        self.observation_space = SimpleNamespace(shape=(5,))
        self.action_space = SimpleNamespace(n=2)

    def _obs(self):
        return np.eye(5, dtype=np.float32)[self.pos]

    def reset(self, seed=None):
        self.pos, self.t = 0, 0
        return self._obs(), {}

    def step(self, action):
        self.t += 1
        self.pos = min(self.pos + 1, 4) if action == 1 else max(self.pos - 1, 0)
        done = self.pos == 4
        return self._obs(), (1.0 if done else -0.01), done, (not done and self.t >= self.limit), {}

    def close(self):
        pass


class EndlessReward:
    """Một observation cố định, một action, reward 1 mỗi bước, không bao giờ terminated, bị cắt sau 10 bước."""

    def __init__(self):
        self.observation_space = SimpleNamespace(shape=(2,))
        self.action_space = SimpleNamespace(n=1)

    def reset(self, seed=None):
        self.t = 0
        return np.array([1.0, 0.5], dtype=np.float32), {}

    def step(self, action):
        self.t += 1
        return np.array([1.0, 0.5], dtype=np.float32), 1.0, False, self.t >= 10, {}

    def close(self):
        pass


def batch_of(rng: np.random.Generator, B: int = 6, obs_dim: int = 3, n_actions: int = 4) -> dict:
    return {
        "obs": torch.tensor(rng.normal(size=(B, obs_dim)), dtype=torch.float32),
        "actions": torch.tensor(rng.integers(0, n_actions, B), dtype=torch.int64),
        "rewards": torch.tensor(rng.normal(size=B), dtype=torch.float32),
        "next_obs": torch.tensor(rng.normal(size=(B, obs_dim)), dtype=torch.float32),
        "terminated": torch.tensor([0, 1, 0, 0, 1, 0][:B], dtype=torch.float32),
    }


def test_replay_buffer_circular(nb):
    buf = nb.ReplayBuffer(capacity=3, obs_dim=2, seed=0)
    assert len(buf) == 0
    for i in range(5):
        buf.add(np.array([i, -i], dtype=np.float32), i % 2, float(i), np.array([i + 1, 0], dtype=np.float32), i == 4)
    assert len(buf) == 3, "đầy thì không lớn thêm"
    seen = set()
    for _ in range(20):
        b = buf.sample(8)
        seen |= set(b["rewards"].tolist())
    assert seen == {2.0, 3.0, 4.0}, "chuyển 0 và 1 (cũ nhất) phải bị ghi đè"


def test_replay_buffer_sample_format(nb):
    buf = nb.ReplayBuffer(capacity=100, obs_dim=3, seed=1)
    obs = np.array([0.5, 1.5, 2.5], dtype=np.float32)
    for i in range(10):
        buf.add(obs * i, i % 3, float(i), obs * (i + 1), i == 9)
    b = buf.sample(32)
    assert set(b) == {"obs", "actions", "rewards", "next_obs", "terminated"}
    assert b["obs"].shape == (32, 3) and b["next_obs"].shape == (32, 3)
    assert b["obs"].dtype == torch.float32 and b["actions"].dtype == torch.int64
    assert b["rewards"].shape == (32,) and b["terminated"].shape == (32,)
    assert b["terminated"].dtype == torch.float32
    i = b["rewards"].long()
    torch.testing.assert_close(b["obs"], torch.tensor(obs) * i[:, None].float())
    torch.testing.assert_close(b["next_obs"], torch.tensor(obs) * (i[:, None] + 1).float())
    assert torch.equal(b["actions"], i % 3)
    assert torch.equal(b["terminated"], (i == 9).float())
    assert set(i.tolist()) <= set(range(10)), "chỉ lấy trong phần đã ghi"


def test_replay_buffer_reproducible(nb):
    def draws():
        buf = nb.ReplayBuffer(50, 1, seed=3)
        for i in range(50):
            buf.add(np.array([i]), 0, float(i), np.array([i]), False)
        return buf.sample(16)["rewards"].tolist()

    assert draws() == draws()


def test_qnetwork_shape(nb):
    torch.manual_seed(0)
    net = nb.QNetwork(4, 3, hidden=16)
    assert net(torch.zeros(5, 4)).shape == (5, 3)
    n = sum(p.numel() for p in net.parameters())
    assert n == 4 * 16 + 16 + 16 * 16 + 16 + 16 * 3 + 3, "hai tầng ẩn rộng hidden"


def test_select_action(nb):
    torch.manual_seed(0)
    net = nb.QNetwork(3, 4, hidden=8)
    obs = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    greedy = int(net(torch.tensor(obs).unsqueeze(0)).argmax())
    rng = np.random.default_rng(0)
    assert all(nb.select_action(net, obs, 0.0, rng, 4) == greedy for _ in range(20))
    picks = [nb.select_action(net, obs, 1.0, rng, 4) for _ in range(400)]
    assert set(picks) == {0, 1, 2, 3} and isinstance(picks[0], int)
    assert nb.linear_epsilon(5_000, 1.0, 0.05, 10_000) == pytest.approx(0.525)
    assert nb.linear_epsilon(20_000, 1.0, 0.05, 10_000) == pytest.approx(0.05)


def test_td_targets_use_target_net(nb):
    torch.manual_seed(1)
    online, target = nb.QNetwork(3, 4, hidden=8), nb.QNetwork(3, 4, hidden=8)
    batch = batch_of(np.random.default_rng(1))
    y = nb.td_targets(batch, target, 0.9)
    assert y.shape == (6,) and not y.requires_grad
    with torch.no_grad():
        expected = batch["rewards"] + 0.9 * (1 - batch["terminated"]) * target(batch["next_obs"]).max(1).values
    torch.testing.assert_close(y, expected)
    assert y[1] == batch["rewards"][1] and y[4] == batch["rewards"][4], "terminated: target chỉ là reward"


def test_td_targets_double(nb):
    torch.manual_seed(2)
    online, target = nb.QNetwork(3, 4, hidden=8), nb.QNetwork(3, 4, hidden=8)
    batch = batch_of(np.random.default_rng(2))
    y = nb.td_targets(batch, target, 0.9, online_net=online)
    with torch.no_grad():
        a = online(batch["next_obs"]).argmax(1, keepdim=True)
        expected = batch["rewards"] + 0.9 * (1 - batch["terminated"]) * target(batch["next_obs"]).gather(1, a).squeeze(1)
    torch.testing.assert_close(y, expected)
    plain = nb.td_targets(batch, target, 0.9)
    assert torch.all(y <= plain + 1e-6), "Double DQN không bao giờ lớn hơn max của target net"


def test_dqn_loss_and_gradients(nb):
    torch.manual_seed(3)
    online, target = nb.QNetwork(3, 4, hidden=8), nb.QNetwork(3, 4, hidden=8)
    batch = batch_of(np.random.default_rng(3))
    loss = nb.dqn_loss(batch, online, target, 0.99)
    with torch.no_grad():
        y = batch["rewards"] + 0.99 * (1 - batch["terminated"]) * target(batch["next_obs"]).max(1).values
    q_sa = online(batch["obs"]).gather(1, batch["actions"][:, None]).squeeze(1)
    ref = F.smooth_l1_loss(q_sa, y)
    assert loss.shape == () and loss.item() == pytest.approx(ref.item(), rel=1e-6)
    loss.backward()
    ref_grads = torch.autograd.grad(F.smooth_l1_loss(online(batch["obs"]).gather(1, batch["actions"][:, None]).squeeze(1), y),
                                    list(online.parameters()))
    for p, g in zip(online.parameters(), ref_grads):
        torch.testing.assert_close(p.grad, g)
    assert all(p.grad is None for p in target.parameters()), "gradient không được đi vào target net"


def test_dqn_loss_double_flag(nb):
    torch.manual_seed(5)
    online, target = nb.QNetwork(3, 4, hidden=8), nb.QNetwork(3, 4, hidden=8)
    batch = batch_of(np.random.default_rng(5))
    q_sa = online(batch["obs"]).gather(1, batch["actions"][:, None]).squeeze(1)
    y_double = nb.td_targets(batch, target, 0.99, online_net=online)
    y_plain = nb.td_targets(batch, target, 0.99)
    assert not torch.allclose(y_double, y_plain), "fixture phải phân biệt được hai kiểu target"
    loss = nb.dqn_loss(batch, online, target, 0.99, double=True)
    assert loss.item() == pytest.approx(F.smooth_l1_loss(q_sa, y_double).item(), rel=1e-6)


def test_dqn_loss_same_net_no_target_gradient(nb):
    torch.manual_seed(4)
    net = nb.QNetwork(3, 4, hidden=8)
    batch = batch_of(np.random.default_rng(4))
    loss = nb.dqn_loss(batch, net, net, 0.99)
    loss.backward()
    with torch.no_grad():
        y = batch["rewards"] + 0.99 * (1 - batch["terminated"]) * net(batch["next_obs"]).max(1).values
    ref = torch.autograd.grad(F.smooth_l1_loss(net(batch["obs"]).gather(1, batch["actions"][:, None]).squeeze(1), y),
                              list(net.parameters()))
    for p, g in zip(net.parameters(), ref):
        torch.testing.assert_close(p.grad, g, msg="target là hằng số: semi-gradient, không lan qua Q(s')")


def test_evaluate_policy_seeds(nb):
    calls = []

    class Recorder(Corridor):
        def reset(self, seed=None):
            calls.append(seed)
            return super().reset(seed)

    out = nb.evaluate_policy(lambda o: 1, Recorder, 3, 40)
    assert isinstance(out, np.ndarray) and out.shape == (3,)
    np.testing.assert_allclose(out, 1 - 0.03)
    assert calls == [40, 41, 42]


def test_train_dqn_solves_corridor(nb):
    h = nb.train_dqn(Corridor, 3_000, seed=0, buffer_size=5_000, batch_size=32, gamma=0.9, lr=5e-3, learning_starts=200,
                     train_freq=1, target_update=100, eps_decay_steps=1_000, hidden=32, eval_every=1_000,
                     eval_episodes=2, eval_seed=0)
    assert set(h) >= {"returns", "end_steps", "losses", "evals", "q_net", "best_state"}
    assert len(h["returns"]) == len(h["end_steps"]) and h["end_steps"] == sorted(h["end_steps"])
    assert len(h["losses"]) == 2_800, "một bước học mỗi bước env từ learning_starts (train_freq = 1)"
    assert [s for s, _ in h["evals"]] == [1_000, 2_000, 3_000]
    net = h["q_net"]
    env = Corridor()
    obs, _ = env.reset()
    for _ in range(4):
        obs, r, te, tr, _ = env.step(int(net(torch.tensor(obs).unsqueeze(0)).argmax()))
    assert te, "policy greedy phải đi thẳng sang phải tới đích trong 4 bước"
    best = nb.QNetwork(5, 2, hidden=32)
    best.load_state_dict(h["best_state"])
    assert evaluate_greedy(best) == pytest.approx(0.97)
    live = h["q_net"].state_dict()
    assert all(h["best_state"][k].data_ptr() != live[k].data_ptr() for k in live), (
        "best_state phải là bản sao (deepcopy), không phải tham chiếu tới trọng số đang train"
    )
    assert max(v for _, v in h["evals"]) == pytest.approx(0.97)


def evaluate_greedy(net) -> float:
    env = Corridor()
    obs, _ = env.reset()
    total, done = 0.0, False
    while not done:
        obs, r, te, tr, _ = env.step(int(net(torch.tensor(obs).unsqueeze(0)).argmax()))
        total += r
        done = te or tr
    return total


def test_train_dqn_reproducible(nb):
    kw = dict(buffer_size=500, batch_size=16, learning_starts=50, train_freq=2, target_update=50, eps_decay_steps=200,
              hidden=16, eval_every=0)
    a = nb.train_dqn(Corridor, 400, seed=5, **kw)
    b = nb.train_dqn(Corridor, 400, seed=5, **kw)
    assert a["returns"] == b["returns"] and a["losses"] == b["losses"]
    assert a["best_state"] is None and a["evals"] == []


def test_train_dqn_epsilon_schedule(nb, monkeypatch):
    seen = []
    real = nb.select_action

    def spy(q_net, obs, epsilon, rng, n_actions):
        seen.append(epsilon)
        return real(q_net, obs, epsilon, rng, n_actions)

    monkeypatch.setattr(nb, "select_action", spy)
    nb.train_dqn(Corridor, 300, seed=0, learning_starts=1_000, eps_start=1.0, eps_end=0.1, eps_decay_steps=200,
                 hidden=8, eval_every=0)
    assert len(seen) == 300, "mỗi bước env chọn action đúng một lần bằng select_action"
    assert seen[0] == pytest.approx(1.0) and seen[100] == pytest.approx(0.55) and seen[250] == pytest.approx(0.1)


def test_train_dqn_truncation_bootstraps(nb):
    h = nb.train_dqn(EndlessReward, 2_500, seed=0, buffer_size=5_000, batch_size=32, gamma=0.9, lr=3e-3,
                     learning_starts=100, train_freq=1, tau=1.0, target_update=50, hidden=16, eval_every=0)
    with torch.no_grad():
        q = h["q_net"](torch.tensor([[1.0, 0.5]])).item()
    assert q == pytest.approx(10.0, abs=1.0), (
        f"Q = {q:.2f}: time limit (truncated) không phải kết thúc, Q phải tiến tới 1/(1-γ) = 10"
    )


def test_train_dqn_uses_target_network(nb):
    """Với target net cập nhật thưa, mạng online ở cuối train khác mạng target; không có target net thì Q đuổi theo chính nó."""
    kw = dict(buffer_size=5_000, batch_size=32, gamma=0.9, lr=3e-3, learning_starts=100, train_freq=1, hidden=16,
              eval_every=0)
    for name, cfg in {"hard": dict(tau=1.0, target_update=10_000), "soft": dict(tau=1e-6)}.items():
        h = nb.train_dqn(EndlessReward, 600, seed=0, **cfg, **kw)
        with torch.no_grad():
            q = h["q_net"](torch.tensor([[1.0, 0.5]])).item()
        assert q == pytest.approx(1.0, abs=0.35), (
            f"{name}: target net gần như đứng yên ở trọng số ban đầu nên target ≈ 1 + 0.9·Q_ban_đầu, Q ≈ 1; đo được {q:.2f}"
        )


def test_train_dqn_soft_update_moves_target(nb):
    kw = dict(buffer_size=5_000, batch_size=32, gamma=0.9, lr=3e-3, learning_starts=100, train_freq=1, hidden=16,
              eval_every=0)
    h = nb.train_dqn(EndlessReward, 2_500, seed=0, tau=0.05, **kw)
    with torch.no_grad():
        q = h["q_net"](torch.tensor([[1.0, 0.5]])).item()
    assert q == pytest.approx(10.0, abs=1.0), f"tau = 0.05: target theo kịp mạng online, Q tiến tới 10; đo được {q:.2f}"
