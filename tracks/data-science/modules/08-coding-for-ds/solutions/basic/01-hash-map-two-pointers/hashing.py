"""Hash map, hash set và two pointers: ba mẫu giải O(n) gặp nhiều nhất ở vòng coding DS."""

from __future__ import annotations

from typing import Hashable, Sequence


def two_sum(nums: Sequence[int], target: int) -> tuple[int, int] | None:
    """Cặp chỉ số (i, j), i < j, với nums[i] + nums[j] == target; None nếu không có.

    Có nhiều cặp: chọn cặp có j nhỏ nhất, rồi tới i nhỏ nhất. Yêu cầu O(n).
    """
    first_index: dict[int, int] = {}
    for j, x in enumerate(nums):
        i = first_index.get(target - x)
        if i is not None:
            return i, j
        first_index.setdefault(x, j)      # giữ chỉ số ĐẦU TIÊN của mỗi giá trị -> i nhỏ nhất
    return None


def first_duplicate(items: Sequence[Hashable]) -> Hashable | None:
    """Giá trị đầu tiên xuất hiện lần thứ hai khi đọc từ trái sang phải; None nếu không trùng.

    Ví dụ ["a", "b", "c", "b", "a"] -> "b". Yêu cầu O(n).
    """
    seen: set[Hashable] = set()
    for x in items:
        if x in seen:
            return x
        seen.add(x)
    return None


def count_pairs_within_budget(prices: Sequence[int], budget: int) -> int:
    """Số cặp (i, j), i < j, với prices[i] + prices[j] <= budget. prices đã sắp xếp tăng dần.

    Yêu cầu O(n) bằng two pointers (O(n log n) cũng chấp nhận).
    """
    left, right, count = 0, len(prices) - 1, 0
    while left < right:
        if prices[left] + prices[right] <= budget:
            count += right - left      # prices[left] ghép được với mọi phần tử trong (left, right]
            left += 1
        else:
            right -= 1
    return count
