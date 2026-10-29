import random
import signal
from contextlib import contextmanager

import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Input lớn: lời giải đúng độ phức tạp chạy dưới 1 giây; lời giải O(n²) (hoặc dò tuyến tính từng
# capacity) cần hàng chục phút. Giới hạn 10 giây rộng để ổn định khi máy bận.
LIMIT = 10


@contextmanager
def time_limit(seconds: float, what: str):
    if not hasattr(signal, "setitimer"):
        pytest.skip("Cần SIGALRM (Linux/macOS) để giới hạn thời gian")

    def handler(signum, frame):
        raise TimeoutError

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except TimeoutError:
        pytest.fail(f"{what}: chạy quá {seconds} giây, chưa đạt độ phức tạp yêu cầu")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@pytest.fixture(scope="module")
def w():
    return ex.module("windows.py")


# ---------- max_events_in_window ----------

def brute_events(ts, window):
    return max((sum(1 for u in ts if t <= u <= t + window) for t in ts), default=0)


def test_events_small(w):
    assert w.max_events_in_window([1, 2, 3, 10, 11], 2) == 3
    assert w.max_events_in_window([0, 5, 10], 4) == 1
    assert w.max_events_in_window([0, 5, 10], 5) == 2          # đoạn đóng [t, t + window]
    assert w.max_events_in_window([], 10) == 0
    assert w.max_events_in_window([3, 3, 3], 0) == 3           # nhiều sự kiện cùng thời điểm


def test_events_matches_brute_force(w):
    rng = random.Random(0)
    for _ in range(300):
        ts = sorted(rng.randint(0, 30) for _ in range(rng.randint(0, 15)))
        window = rng.randint(0, 10)
        assert w.max_events_in_window(ts, window) == brute_events(ts, window), (ts, window)


def test_events_large_input(w):
    n = 200_000
    ts = list(range(n))
    with time_limit(LIMIT, "max_events_in_window"):
        assert w.max_events_in_window(ts, n // 2) == n // 2 + 1


# ---------- longest_run_within_budget ----------

def brute_run(values, budget):
    best = 0
    for i in range(len(values)):
        for j in range(i, len(values)):
            if sum(values[i:j + 1]) <= budget:
                best = max(best, j - i + 1)
    return best


def test_run_small(w):
    assert w.longest_run_within_budget([3, 1, 2, 1, 5], 4) == 3     # 1, 2, 1
    assert w.longest_run_within_budget([5, 6], 4) == 0
    assert w.longest_run_within_budget([], 4) == 0
    assert w.longest_run_within_budget([0, 0, 0], 0) == 3


def test_run_matches_brute_force(w):
    rng = random.Random(1)
    for _ in range(300):
        values = [rng.randint(0, 9) for _ in range(rng.randint(0, 12))]
        budget = rng.randint(0, 25)
        assert w.longest_run_within_budget(values, budget) == brute_run(values, budget), (values, budget)


def test_run_large_input(w):
    n = 200_000
    values = [1] * n
    with time_limit(LIMIT, "longest_run_within_budget"):
        assert w.longest_run_within_budget(values, n // 2) == n // 2


# ---------- min_daily_capacity ----------

def feasible(weights, days, cap):
    used, load = 1, 0
    for x in weights:
        if load + x > cap:
            used, load = used + 1, 0
        load += x
    return used <= days


def test_capacity_small(w):
    assert w.min_daily_capacity([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5) == 15
    assert w.min_daily_capacity([3, 2, 2, 4, 1, 4], 3) == 6
    assert w.min_daily_capacity([1, 2, 3, 1, 1], 4) == 3
    assert w.min_daily_capacity([7], 3) == 7
    assert w.min_daily_capacity([5, 5, 5], 1) == 15


def test_capacity_is_minimal_and_feasible(w):
    rng = random.Random(2)
    for _ in range(200):
        weights = [rng.randint(1, 20) for _ in range(rng.randint(1, 12))]
        days = rng.randint(1, len(weights))
        cap = w.min_daily_capacity(weights, days)
        assert feasible(weights, days, cap), (weights, days, cap)
        assert cap == max(weights) or not feasible(weights, days, cap - 1), (weights, days, cap)


def test_capacity_large_input(w):
    rng = random.Random(3)
    weights = [rng.randint(1, 1000) for _ in range(100_000)]
    with time_limit(LIMIT, "min_daily_capacity"):
        cap = w.min_daily_capacity(weights, 10)
    assert feasible(weights, 10, cap) and not feasible(weights, 10, cap - 1)
