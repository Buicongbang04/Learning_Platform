"""Heap cho dữ liệu dạng luồng: top-k, trung vị chạy, trộn k luồng đã sắp xếp."""

from __future__ import annotations

import heapq
from typing import Iterable, Iterator


def top_k_sellers(sales: Iterable[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    """k seller có tổng doanh thu lớn nhất, dạng [(seller_id, tổng), ...].

    Sắp theo tổng giảm dần; bằng nhau thì seller_id tăng dần. `sales` có thể là iterator chỉ đọc
    được một lần. Yêu cầu O(n + m log k) với m là số seller.
    """
    # TODO: cộng dồn bằng dict, rồi lấy k phần tử lớn nhất bằng heap (heapq.nsmallest với key phù hợp)
    raise NotImplementedError


def running_median(stream: Iterable[float]) -> list[float]:
    """Trung vị của các phần tử đã thấy, sau mỗi phần tử. Số phần tử chẵn: trung bình hai phần tử giữa.

    Yêu cầu O(n log n): hai heap (max-heap nửa dưới, min-heap nửa trên).
    """
    # TODO: heapq chỉ có min-heap -> lưu số âm cho max-heap; sau mỗi lần thêm, cân lại hai heap
    raise NotImplementedError


def merge_sorted_streams(*streams: Iterable) -> Iterator:
    """Trộn các luồng đã sắp xếp tăng dần thành một luồng tăng dần, LAZY (luồng có thể vô hạn).

    Hai phần tử bằng nhau: phần tử của luồng đứng trước ra trước. Không dùng heapq.merge.
    """
    # TODO: heap chứa (giá trị, chỉ số luồng, iterator); pop nhỏ nhất, yield, đẩy phần tử kế tiếp
    #       của chính luồng đó vào heap
    raise NotImplementedError
    yield  # biến hàm thành generator
