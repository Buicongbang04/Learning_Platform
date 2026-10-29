import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Marketplace giả lập: mỗi period (ví dụ 30 phút) có ~1 000 user, mỗi user đặt đơn với xác suất 10%.
# Treatment (giảm phí ship) làm xác suất đặt tăng 50%. Chỉ có 110 shipper mỗi period: đơn vượt quá
# không được phục vụ, một nửa số đơn đó đặt lại ở period sau (carryover).
BASE_P, LIFT, CAPACITY, RETRY, USERS = 0.10, 0.5, 110, 0.5, 1000


def simulate(n_periods: int, arms=None, seed: int = 0):
    """arms=None: chia user 50/50 trong mỗi period (A/B theo user). arms: mảng 0/1 mỗi period.

    Trả (periods, users): periods có cột period, treat, users, orders (đơn được phục vụ);
    users (chỉ khi arms=None) mỗi dòng một user-period, cột period, treat, orders.
    """
    rng = np.random.default_rng(seed)
    retry = 0
    periods, users = [], []
    for h in range(n_periods):
        n = rng.poisson(USERS)
        n_t = rng.binomial(n, 0.5) if arms is None else (n if arms[h] == 1 else 0)
        n_c = n - n_t
        o_t = rng.binomial(n_t, BASE_P * (1 + LIFT))
        o_c = rng.binomial(n_c, BASE_P)
        total = o_t + o_c + retry
        done = min(total, CAPACITY)
        f_t, f_c, _ = rng.multivariate_hypergeometric([o_t, o_c, retry], done)
        retry = rng.binomial(total - done, RETRY)
        periods.append({"period": h, "treat": -1 if arms is None else int(arms[h]), "users": n, "orders": done})
        if arms is None:
            for treat, size, served in ((1, n_t, f_t), (0, n_c, f_c)):
                v = np.zeros(size)
                v[:served] = 1
                users.append(pd.DataFrame({"period": h, "treat": treat, "orders": v}))
    return pd.DataFrame(periods), (pd.concat(users, ignore_index=True) if users else None)


@pytest.fixture(scope="module")
def sb():
    return ex.module("switchback.py")


@pytest.fixture(scope="module")
def global_effect():
    """Tác động thật khi bật cho TẤT CẢ so với tắt cho tất cả: đơn được phục vụ mỗi user."""
    on, _ = simulate(3000, np.ones(3000, int), seed=1)
    off, _ = simulate(3000, np.zeros(3000, int), seed=2)
    return (on.orders / on.users).mean() - (off.orders / off.users).mean()


def test_schedule_blocks(sb):
    s = sb.switchback_schedule(100, block=4, seed=0)
    assert s.shape == (100,) and set(np.unique(s)) <= {0, 1}
    blocks = s.reshape(25, 4)
    assert (blocks == blocks[:, :1]).all()                 # cả block cùng nhánh
    assert abs(blocks[:, 0].sum() - 12.5) <= 0.5           # 12 hoặc 13 block treatment
    assert np.array_equal(s, sb.switchback_schedule(100, block=4, seed=0))
    assert not np.array_equal(s, sb.switchback_schedule(100, block=4, seed=1))


def test_schedule_partial_last_block(sb):
    s = sb.switchback_schedule(10, block=4, seed=3)
    assert s.shape == (10,)
    assert len(set(s[8:])) == 1 and len(set(s[:4])) == 1


def test_switchback_estimate_hand_example(sb):
    periods = pd.DataFrame({
        "period": [0, 1, 2, 3, 4, 5, 6, 7],
        "treat": [1, 1, 1, 0, 0, 0, 1, 1],
        "users": [100] * 8,
        "orders": [20, 12, 14, 30, 10, 12, 50, 16],
    })
    out = sb.switchback_estimate(periods, burn_in=0)
    assert out["n_used"] == 8
    assert out["diff"] == pytest.approx(np.mean([0.20, 0.12, 0.14, 0.50, 0.16]) - np.mean([0.30, 0.10, 0.12]))
    t0, c0 = [0.20, 0.12, 0.14, 0.50, 0.16], [0.30, 0.10, 0.12]
    assert out["se"] == pytest.approx(np.sqrt(np.var(t0, ddof=1) / 5 + np.var(c0, ddof=1) / 3))
    burned = sb.switchback_estimate(periods, burn_in=1)   # bỏ period 0, 3, 6
    assert burned["n_used"] == 5
    assert burned["diff"] == pytest.approx(np.mean([0.12, 0.14, 0.16]) - np.mean([0.10, 0.12]))
    assert burned["se"] == pytest.approx(np.sqrt(np.var([0.12, 0.14, 0.16], ddof=1) / 3 + np.var([0.10, 0.12], ddof=1) / 2))
    shuffled = sb.switchback_estimate(periods.sample(frac=1, random_state=0), burn_in=1)
    assert shuffled["diff"] == pytest.approx(burned["diff"])   # không phụ thuộc thứ tự dòng


def test_user_split_estimate_values(sb):
    users = pd.DataFrame({"treat": [1, 1, 1, 0, 0, 0, 0], "orders": [1.0, 0, 1, 0, 0, 1, 0]})
    out = sb.user_split_estimate(users)
    assert out["diff"] == pytest.approx(2 / 3 - 1 / 4)
    assert out["se"] == pytest.approx(np.sqrt(np.var([1, 0, 1], ddof=1) / 3 + np.var([0, 0, 1, 0], ddof=1) / 4))


def test_user_split_overstates_effect(sb, global_effect):
    _, users = simulate(200, None, seed=10)
    out = sb.user_split_estimate(users)
    # treatment "cướp" shipper của control: hiệu A/B theo user lớn gấp mấy lần tác động thật
    assert out["diff"] > 2.5 * global_effect
    assert out["diff"] - 3 * out["se"] > global_effect     # và CI rất tự tin vào con số sai


def test_switching_every_period_without_burn_in_is_biased(sb, global_effect):
    arms = np.arange(600) % 2
    periods, _ = simulate(600, arms, seed=11)
    out = sb.switchback_estimate(periods, burn_in=0)
    assert out["diff"] < 0.6 * global_effect


def test_blocks_with_burn_in_recover_global_effect(sb, global_effect):
    raw, burned = [], []
    for seed in range(5):
        arms = sb.switchback_schedule(600, block=6, seed=seed)
        periods, _ = simulate(600, arms, seed=100 + seed)
        raw.append(sb.switchback_estimate(periods, burn_in=0)["diff"])
        burned.append(sb.switchback_estimate(periods, burn_in=2)["diff"])
    # bỏ 2 period đầu mỗi block làm giảm thiên lệch do carryover, và về gần tác động thật
    assert np.mean(burned) > np.mean(raw)
    assert np.mean(burned) == pytest.approx(global_effect, rel=0.15)
