"""Hash map, hash set và two pointers: ba mẫu giải O(n) gặp nhiều nhất ở vòng coding DS."""

from __future__ import annotations

from typing import Hashable, Sequence


def two_sum(nums: Sequence[int], target: int) -> tuple[int, int] | None:
    """Cặp chỉ số (i, j), i < j, với nums[i] + nums[j] == target; None nếu không có.

    Có nhiều cặp: chọn cặp có j nhỏ nhất, rồi tới i nhỏ nhất. Yêu cầu O(n).
    """
    # TODO: duyệt j từ trái sang phải, tra số bù target - nums[j] trong một dict giá trị -> chỉ số
    raise NotImplementedError


def first_duplicate(items: Sequence[Hashable]) -> Hashable | None:
    """Giá trị đầu tiên xuất hiện lần thứ hai khi đọc từ trái sang phải; None nếu không trùng.

    Ví dụ ["a", "b", "c", "b", "a"] -> "b". Yêu cầu O(n).
    """
    # TODO
    raise NotImplementedError


def count_pairs_within_budget(prices: Sequence[int], budget: int) -> int:
    """Số cặp (i, j), i < j, với prices[i] + prices[j] <= budget. prices đã sắp xếp tăng dần.

    Yêu cầu O(n) bằng two pointers (O(n log n) cũng chấp nhận).
    """
    # TODO: con trỏ trái ở đầu, phải ở cuối; nếu tổng <= budget thì mọi phần tử giữa hai con trỏ
    #       đều ghép được với phần tử bên trái
    raise NotImplementedError
