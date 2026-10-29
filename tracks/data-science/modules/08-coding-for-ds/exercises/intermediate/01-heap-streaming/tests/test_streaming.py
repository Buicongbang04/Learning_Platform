import itertools
import random
import signal
import statistics
from contextlib import contextmanager

import pytest

from testkit import Exercise

ex = Exercise(__file__)

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
def s():
    return ex.module("streaming.py")


# ---------- top_k_sellers ----------

def test_top_k_aggregates_and_sorts(s):
    sales = [("a", 10.0), ("b", 5.0), ("a", 1.0), ("c", 20.0), ("b", 7.0)]
    assert s.top_k_sellers(sales, 2) == [("c", 20.0), ("b", 12.0)]


def test_top_k_tie_break_by_seller_id(s):
    sales = [("z", 5.0), ("m", 5.0), ("a", 5.0), ("q", 1.0)]
    assert s.top_k_sellers(sales, 2) == [("a", 5.0), ("m", 5.0)]


def test_top_k_larger_than_number_of_sellers(s):
    assert s.top_k_sellers([("x", 1.0), ("y", 2.0)], 10) == [("y", 2.0), ("x", 1.0)]
    assert s.top_k_sellers([], 3) == []


def test_top_k_accepts_one_pass_iterator(s):
    rng = random.Random(0)
    data = [(f"s{rng.randint(0, 50)}", float(rng.randint(1, 100))) for _ in range(2000)]
    totals = {}
    for seller, amount in data:
        totals[seller] = totals.get(seller, 0.0) + amount
    expected = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    assert s.top_k_sellers(iter(data), 5) == expected       # iterator chỉ đọc được một lần


# ---------- running_median ----------

def test_running_median_small(s):
    assert s.running_median([5, 15, 1, 3]) == [5.0, 10.0, 5.0, 4.0]
    assert s.running_median([]) == []
    assert s.running_median([2, 2, 2]) == [2.0, 2.0, 2.0]


def test_running_median_matches_statistics(s):
    rng = random.Random(1)
    for _ in range(50):
        xs = [rng.randint(-50, 50) for _ in range(rng.randint(1, 60))]
        expected = [float(statistics.median(xs[: i + 1])) for i in range(len(xs))]
        assert s.running_median(xs) == pytest.approx(expected)


def test_running_median_large_input(s):
    # Hai heap: O(n log n), khoảng 1 giây cho 1 triệu phần tử. bisect.insort là O(n) mỗi lần chèn
    # (dời phần tử trong list) nên tổng O(n²): vài chục giây trở lên; sort lại mỗi bước còn chậm hơn.
    rng = random.Random(2)
    xs = [rng.random() for _ in range(1_000_000)]
    with time_limit(LIMIT, "running_median"):
        out = s.running_median(xs)
    assert len(out) == len(xs)
    assert out[-1] == pytest.approx(statistics.median(xs))
    assert out[999] == pytest.approx(statistics.median(xs[:1000]))


# ---------- merge_sorted_streams ----------

def test_merge_finite(s):
    assert list(s.merge_sorted_streams([1, 4, 9], [2, 3, 10], [], [5])) == [1, 2, 3, 4, 5, 9, 10]
    assert list(s.merge_sorted_streams()) == []


def test_merge_ties_prefer_earlier_stream(s):
    a = [(1, "a1"), (2, "a2")]
    b = [(1, "b1"), (2, "b2")]
    out = list(s.merge_sorted_streams(iter(a), iter(b)))
    assert out == [(1, "a1"), (1, "b1"), (2, "a2"), (2, "b2")]


def guarded(stream, limit=100_000):
    """Luồng "vô hạn" có rào chắn: đọc quá `limit` phần tử nghĩa là hàm đang đọc hết luồng."""
    for i, x in enumerate(stream):
        if i >= limit:
            raise RuntimeError("Đọc quá nhiều phần tử: merge_sorted_streams chưa lazy")
        yield x


def test_merge_is_lazy_on_infinite_streams(s):
    evens = guarded(itertools.count(0, 2))
    odds = guarded(itertools.count(1, 2))
    tens = guarded(itertools.count(0, 10))
    merged = s.merge_sorted_streams(evens, odds, tens)
    head = list(itertools.islice(merged, 12))
    assert head == [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
