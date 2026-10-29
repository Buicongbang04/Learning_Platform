import math
import random

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def ag():
    return ex.module("autograd.py")


def test_add_mul_gradients(ag):
    a, b = ag.Value(2.0), ag.Value(-3.0)
    out = a * b + a            # d/da = b + 1 = -2, d/db = a = 2
    out.backward()
    assert out.data == pytest.approx(-4.0)
    assert a.grad == pytest.approx(-2.0)
    assert b.grad == pytest.approx(2.0)
    assert out.grad == pytest.approx(1.0)


def test_reused_node_accumulates_gradient(ag):
    a = ag.Value(3.0)
    out = a * a + a            # 2a + 1 = 7: dùng a ba lần, gradient phải cộng dồn
    out.backward()
    assert a.grad == pytest.approx(7.0)


def test_python_numbers_on_both_sides(ag):
    a = ag.Value(4.0)
    out = 2 * a + 1 - a / 2 + 3 / a - (1 - a) + a ** 3
    out.backward()
    expected = 2 * 4 + 1 - 4 / 2 + 3 / 4 - (1 - 4) + 4 ** 3
    assert out.data == pytest.approx(expected)
    assert a.grad == pytest.approx(2 - 0.5 - 3 / 16 + 1 + 3 * 16)


def test_relu_tanh_exp_log_match_torch(ag):
    for x in (-1.3, -0.2, 0.4, 1.7):
        v = ag.Value(x)
        out = v.relu() + v.tanh() * v.exp() + (v * v + 1).log()
        out.backward()
        t = torch.tensor(x, dtype=torch.float64, requires_grad=True)
        ref = torch.relu(t) + torch.tanh(t) * torch.exp(t) + torch.log(t * t + 1)
        ref.backward()
        assert out.data == pytest.approx(ref.item(), rel=1e-9)
        assert v.grad == pytest.approx(t.grad.item(), rel=1e-9)


def test_relu_gradient_is_zero_for_negative_input(ag):
    a = ag.Value(-2.0)
    a.relu().backward()
    assert a.grad == 0.0


def _random_expression(rng, leaves, depth):
    """Biểu thức ngẫu nhiên dùng chung cho Value và torch (op chạy được trên cả hai)."""
    if depth == 0:
        return rng.choice(leaves)
    left = _random_expression(rng, leaves, depth - 1)
    right = _random_expression(rng, leaves, depth - 1)
    op = rng.choice(["add", "mul", "sub", "tanh", "pow", "div"])
    if op == "add":
        return lambda env: left(env) + right(env)
    if op == "mul":
        return lambda env: left(env) * right(env)
    if op == "sub":
        return lambda env: left(env) - right(env)
    if op == "tanh":
        return lambda env: left(env).tanh() + right(env)
    if op == "pow":
        return lambda env: left(env) ** 2 + right(env)
    return lambda env: left(env) / (right(env) * right(env) + 1.5)


@pytest.mark.parametrize("seed", range(8))
def test_random_expressions_match_torch(ag, seed):
    rng = random.Random(seed)
    names = ["x", "y", "z"]
    leaves = [lambda env, n=n: env[n] for n in names]
    expr = _random_expression(rng, leaves, depth=4)
    values = {n: rng.uniform(-1.5, 1.5) for n in names}

    mine = {n: ag.Value(v) for n, v in values.items()}
    out = expr(mine)
    out.backward()

    ref_env = {n: torch.tensor(v, dtype=torch.float64, requires_grad=True) for n, v in values.items()}
    ref = expr(ref_env)
    ref.backward()

    assert out.data == pytest.approx(ref.item(), rel=1e-9, abs=1e-12)
    for n in names:
        expected = 0.0 if ref_env[n].grad is None else ref_env[n].grad.item()
        assert mine[n].grad == pytest.approx(expected, rel=1e-8, abs=1e-10)


def test_deep_graph_does_not_hit_recursion_limit(ag):
    x = ag.Value(1.0)
    y = x
    for _ in range(5000):            # sâu hơn giới hạn đệ quy mặc định (1000) của Python
        y = y * 1.0001
    y.backward()
    assert x.grad == pytest.approx(1.0001 ** 5000, rel=1e-9)


def test_backward_on_leaf_and_untouched_nodes(ag):
    a, b = ag.Value(1.5), ag.Value(2.0)
    c = a * 3                         # b không tham gia
    c.backward()
    assert a.grad == pytest.approx(3.0)
    assert b.grad == 0.0


def test_fit_line_recovers_parameters(ag):
    xs = [i / 10 for i in range(-10, 11)]
    ys = [2.0 * x - 1.0 for x in xs]
    w, b = ag.fit_line(xs, ys, lr=0.1, steps=300)
    assert isinstance(w, float) and isinstance(b, float)
    assert w == pytest.approx(2.0, abs=1e-3)
    assert b == pytest.approx(-1.0, abs=1e-3)


def test_fit_line_loss_is_mean_squared_error(ag):
    # Một bước GD từ w = b = 0 với lr nhỏ: gradient của MSE trung bình là -2 mean(x y), -2 mean(y)
    xs, ys = [1.0, 2.0, 3.0], [1.0, 3.0, 2.0]
    w, b = ag.fit_line(xs, ys, lr=0.01, steps=1)
    assert w == pytest.approx(0.01 * 2 * (1 + 6 + 6) / 3)
    assert b == pytest.approx(0.01 * 2 * (1 + 3 + 2) / 3)
    assert not math.isnan(w)
