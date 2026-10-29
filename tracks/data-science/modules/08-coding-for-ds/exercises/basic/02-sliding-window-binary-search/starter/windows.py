"""Sliding window và binary search trên đáp án."""

from __future__ import annotations

from typing import Sequence


def max_events_in_window(timestamps: Sequence[float], window: float) -> int:
    """Số sự kiện lớn nhất nằm trong một đoạn đóng [t, t + window] bất kỳ.

    timestamps đã sắp xếp tăng dần. Ví dụ: số đơn nhiều nhất trong 1 giờ bất kỳ (tải đỉnh).
    Yêu cầu O(n).
    """
    # TODO: con trỏ phải duyệt từng sự kiện; con trỏ trái tiến lên khi đoạn rộng quá window
    raise NotImplementedError


def longest_run_within_budget(values: Sequence[int], budget: int) -> int:
    """Độ dài đoạn con liên tiếp dài nhất có tổng <= budget. values không âm. Yêu cầu O(n)."""
    # TODO: cửa sổ co giãn; giữ tổng hiện tại, co bên trái khi tổng vượt budget
    raise NotImplementedError


def min_daily_capacity(weights: Sequence[int], days: int) -> int:
    """Sức chứa nhỏ nhất mỗi ngày để giao hết các kiện theo đúng thứ tự trong tối đa `days` ngày.

    Mỗi ngày chất kiện theo thứ tự cho tới khi kiện tiếp theo làm vượt sức chứa thì sang ngày mới.
    weights khác rỗng, mọi phần tử dương; days >= 1.
    Yêu cầu O(n log(sum(weights))).
    """
    # TODO: hàm "giao kịp với capacity c không?" là đơn điệu theo c -> binary search trên c,
    #       trong đoạn [max(weights), sum(weights)]
    raise NotImplementedError
