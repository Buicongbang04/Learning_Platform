"""Sliding window và binary search trên đáp án."""

from __future__ import annotations

from typing import Sequence


def max_events_in_window(timestamps: Sequence[float], window: float) -> int:
    """Số sự kiện lớn nhất nằm trong một đoạn đóng [t, t + window] bất kỳ.

    timestamps đã sắp xếp tăng dần. Ví dụ: số đơn nhiều nhất trong 1 giờ bất kỳ (tải đỉnh).
    Yêu cầu O(n).
    """
    best, left = 0, 0
    for right, t in enumerate(timestamps):
        while t - timestamps[left] > window:
            left += 1
        best = max(best, right - left + 1)
    return best


def longest_run_within_budget(values: Sequence[int], budget: int) -> int:
    """Độ dài đoạn con liên tiếp dài nhất có tổng <= budget. values không âm. Yêu cầu O(n)."""
    best, left, total = 0, 0, 0
    for right, x in enumerate(values):
        total += x
        while total > budget:            # values không âm nên co trái luôn làm tổng giảm
            total -= values[left]
            left += 1
        best = max(best, right - left + 1)
    return best


def _days_needed(weights: Sequence[int], capacity: int) -> int:
    days, load = 1, 0
    for x in weights:
        if load + x > capacity:
            days, load = days + 1, 0
        load += x
    return days


def min_daily_capacity(weights: Sequence[int], days: int) -> int:
    """Sức chứa nhỏ nhất mỗi ngày để giao hết các kiện theo đúng thứ tự trong tối đa `days` ngày.

    Mỗi ngày chất kiện theo thứ tự cho tới khi kiện tiếp theo làm vượt sức chứa thì sang ngày mới.
    weights khác rỗng, mọi phần tử dương; days >= 1.
    Yêu cầu O(n log(sum(weights))).
    """
    lo, hi = max(weights), sum(weights)    # lo: phải chở được kiện nặng nhất; hi: chở hết trong 1 ngày
    while lo < hi:                          # bất biến: đáp án nằm trong [lo, hi]
        mid = (lo + hi) // 2
        if _days_needed(weights, mid) <= days:
            hi = mid                        # mid đủ -> đáp án <= mid
        else:
            lo = mid + 1                    # mid thiếu -> đáp án > mid
    return lo
