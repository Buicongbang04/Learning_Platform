import os
import subprocess
import sys

import pytest

from testkit import Exercise

ex = Exercise(__file__)
IDS = [f"req-{i}" for i in range(2000)]


@pytest.fixture(scope="module")
def routing():
    return ex.module("routing.py")


@pytest.mark.parametrize("weight", [0.05, 0.1, 0.25, 0.5])
def test_canary_share_matches_weight(routing, weight):
    share = sum(routing.route(i, weight) == "canary" for i in IDS) / len(IDS)
    assert abs(share - weight) <= 0.03, f"Tỉ lệ canary {share:.3f}, trọng số {weight}"


def test_same_id_same_branch(routing):
    first = [routing.route(i, 0.3) for i in IDS[:300]]
    second = [routing.route(i, 0.3) for i in IDS[:300]]
    assert first == second, "Cùng request_id phải luôn vào cùng nhánh"


def test_extreme_weights(routing):
    assert {routing.route(i, 0.0) for i in IDS[:200]} == {"stable"}
    assert {routing.route(i, 1.0) for i in IDS[:200]} == {"canary"}


@pytest.mark.parametrize("weight", [-0.1, 1.1])
def test_invalid_weight(routing, weight):
    with pytest.raises(ValueError):
        routing.route("req-1", weight)


def test_raising_weight_never_moves_canary_back(routing):
    at_10 = {i for i in IDS if routing.route(i, 0.10) == "canary"}
    at_30 = {i for i in IDS if routing.route(i, 0.30) == "canary"}
    assert at_10 <= at_30, "Tăng trọng số chỉ được thêm request vào canary, không chuyển request đang ở canary về stable"


def test_stable_across_processes(routing):
    code = (
        "import importlib.util,sys;"
        "s=importlib.util.spec_from_file_location('r',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "print(''.join('c' if m.route(f'req-{i}',0.5)=='canary' else 's' for i in range(200)))"
    )
    path = str(ex.path("routing.py"))
    outputs = {
        subprocess.run([sys.executable, "-c", code, path], capture_output=True, text=True, timeout=60,
                       env={**os.environ, "PYTHONHASHSEED": seed}).stdout
        for seed in ("1", "2", "3")
    }
    assert len(outputs) == 1 and outputs != {""}, "Kết quả thay đổi giữa các lần chạy: đừng dùng hash() hay random của Python"


def test_salt_makes_experiments_independent(routing):
    a = {i for i in IDS if routing.route(i, 0.5, salt="exp-a") == "canary"}
    b = {i for i in IDS if routing.route(i, 0.5, salt="exp-b") == "canary"}
    overlap = len(a & b) / len(IDS)
    assert 0.20 <= overlap <= 0.30, f"Hai thí nghiệm khác salt phải độc lập (~25% trùng), đang {overlap:.2f}"


def test_ab_assignment_follows_weights(routing):
    weights = {"control": 0.5, "variant_a": 0.3, "variant_b": 0.2}
    users = [f"user-{i}" for i in range(3000)]
    counts = {name: 0 for name in weights}
    for user in users:
        counts[routing.assign_variant(user, "pricing-v2", weights)] += 1
    for name, weight in weights.items():
        assert abs(counts[name] / len(users) - weight) <= 0.03, (name, counts)


def test_ab_assignment_is_sticky_and_order_independent(routing):
    weights = {"control": 0.5, "variant_a": 0.3, "variant_b": 0.2}
    reordered = {"variant_b": 0.2, "control": 0.5, "variant_a": 0.3}
    for user in (f"user-{i}" for i in range(300)):
        assert routing.assign_variant(user, "e", weights) == routing.assign_variant(user, "e", reordered)


def test_ab_zero_weight_and_invalid(routing):
    assert {routing.assign_variant(f"u{i}", "e", {"a": 1.0, "b": 0.0}) for i in range(300)} == {"a"}
    for bad in ({"a": 0.5, "b": 0.4}, {"a": 1.2, "b": -0.2}, {}):
        with pytest.raises(ValueError):
            routing.assign_variant("u", "e", bad)
