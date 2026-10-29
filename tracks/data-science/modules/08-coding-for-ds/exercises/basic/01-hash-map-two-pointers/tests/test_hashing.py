import random
import signal
from contextlib import contextmanager
from itertools import combinations

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Các test "input lớn" chạy với n = 200 000. Lời giải O(n) hoặc O(n log n) bằng Python mất dưới
# 1 giây; lời giải O(n²) cần khoảng 2·10^10 phép so sánh, tức hàng chục phút. Giới hạn 10 giây
# rất rộng để test vẫn ổn khi máy đang bận.
LIMIT = 10
N = 200_000


@contextmanager
def time_limit(seconds: float):
    if not hasattr(signal, "setitimer"):
        pytest.skip("Cần SIGALRM (Linux/macOS) để giới hạn thời gian")

    def handler(signum, frame):
        raise TimeoutError

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except TimeoutError:
        pytest.fail(f"Chạy quá {seconds} giây với n = {N}: thuật toán đang là O(n²)?")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@pytest.fixture(scope="module")
def h():
    return ex.module("hashing.py")


# ---------- two_sum ----------

def test_two_sum_basic(h):
    assert h.two_sum([3, 8, 1, 5], 6) == (2, 3)
    assert h.two_sum([2, 7, 11, 15], 9) == (0, 1)
    assert h.two_sum([1, 2, 3], 100) is None
    assert h.two_sum([], 0) is None


def test_two_sum_same_value_needs_two_indices(h):
    assert h.two_sum([3, 4], 6) is None          # không được dùng một phần tử hai lần
    assert h.two_sum([3, 4, 3], 6) == (0, 2)


def test_two_sum_returns_smallest_j_then_smallest_i(h):
    # (0, 3), (1, 3) và (2, 4) đều hợp lệ; j nhỏ nhất là 3, trong đó i nhỏ nhất là 0
    assert h.two_sum([1, 1, 4, 5, 2], 6) == (0, 3)


def test_two_sum_matches_brute_force(h):
    rng = random.Random(0)
    for _ in range(300):
        nums = [rng.randint(-10, 10) for _ in range(rng.randint(0, 12))]
        target = rng.randint(-15, 15)
        pairs = [(i, j) for i, j in combinations(range(len(nums)), 2) if nums[i] + nums[j] == target]
        expected = min(pairs, key=lambda p: (p[1], p[0])) if pairs else None
        assert h.two_sum(nums, target) == expected, (nums, target)


def test_two_sum_large_input(h):
    nums = list(range(0, 2 * N, 2)) + [1]          # chỉ một cặp: số chẵn cuối + số 1 ở cuối
    with time_limit(LIMIT):
        assert h.two_sum(nums, 2 * (N - 1) + 1) == (N - 1, N)


# ---------- first_duplicate ----------

def test_first_duplicate_basic(h):
    assert h.first_duplicate(["a", "b", "c", "b", "a"]) == "b"   # "b" lặp lại ở vị trí 3, sớm hơn "a" ở vị trí 4
    assert h.first_duplicate([1, 2, 3]) is None
    assert h.first_duplicate([]) is None
    assert h.first_duplicate([7, 7]) == 7


def test_first_duplicate_large_input(h):
    items = [f"order-{i}" for i in range(N)] + ["order-123"]
    with time_limit(LIMIT):
        assert h.first_duplicate(items) == "order-123"


# ---------- count_pairs_within_budget ----------

def brute_pairs(prices, budget):
    return sum(1 for a, b in combinations(prices, 2) if a + b <= budget)


def test_count_pairs_small(h):
    assert h.count_pairs_within_budget([1, 2, 3, 4, 5], 6) == 6   # (1,2) (1,3) (1,4) (1,5) (2,3) (2,4)
    assert h.count_pairs_within_budget([10, 20], 5) == 0
    assert h.count_pairs_within_budget([5], 100) == 0
    assert h.count_pairs_within_budget([], 100) == 0


def test_count_pairs_with_duplicates_matches_brute_force(h):
    rng = random.Random(1)
    for _ in range(300):
        prices = sorted(rng.randint(0, 20) for _ in range(rng.randint(0, 15)))
        budget = rng.randint(0, 40)
        assert h.count_pairs_within_budget(prices, budget) == brute_pairs(prices, budget), (prices, budget)


def test_count_pairs_large_input(h):
    rng = np.random.default_rng(2)
    prices = np.sort(rng.integers(1, 1_000_000, N))
    budget = 1_000_000
    right = np.searchsorted(prices, budget - prices, side="right")
    expected = int(np.clip(right - np.arange(1, N + 1), 0, None).sum())
    with time_limit(LIMIT):
        assert h.count_pairs_within_budget(prices.tolist(), budget) == expected
