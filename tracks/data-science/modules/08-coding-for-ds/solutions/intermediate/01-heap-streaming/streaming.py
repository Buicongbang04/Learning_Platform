"""Heap cho dữ liệu dạng luồng: top-k, trung vị chạy, trộn k luồng đã sắp xếp."""

from __future__ import annotations

import heapq
from typing import Iterable, Iterator


def top_k_sellers(sales: Iterable[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    """k seller có tổng doanh thu lớn nhất, dạng [(seller_id, tổng), ...].

    Sắp theo tổng giảm dần; bằng nhau thì seller_id tăng dần. `sales` có thể là iterator chỉ đọc
    được một lần. Yêu cầu O(n + m log k) với m là số seller.
    """
    totals: dict[str, float] = {}
    for seller, amount in sales:
        totals[seller] = totals.get(seller, 0.0) + amount
    # nsmallest giữ một heap cỡ k: O(m log k). Key (-tổng, id) cho đúng thứ tự cả khi bằng nhau.
    return heapq.nsmallest(k, totals.items(), key=lambda kv: (-kv[1], kv[0]))


def running_median(stream: Iterable[float]) -> list[float]:
    """Trung vị của các phần tử đã thấy, sau mỗi phần tử. Số phần tử chẵn: trung bình hai phần tử giữa.

    Yêu cầu O(n log n): hai heap (max-heap nửa dưới, min-heap nửa trên).
    """
    low: list[float] = []    # max-heap (lưu số âm): nửa dưới, được phép nhiều hơn nửa trên 1 phần tử
    high: list[float] = []   # min-heap: nửa trên
    out: list[float] = []
    for x in stream:
        if low and x > -low[0]:
            heapq.heappush(high, x)
        else:
            heapq.heappush(low, -x)
        if len(low) > len(high) + 1:
            heapq.heappush(high, -heapq.heappop(low))
        elif len(high) > len(low):
            heapq.heappush(low, -heapq.heappop(high))
        out.append(float(-low[0]) if len(low) > len(high) else (-low[0] + high[0]) / 2)
    return out


def merge_sorted_streams(*streams: Iterable) -> Iterator:
    """Trộn các luồng đã sắp xếp tăng dần thành một luồng tăng dần, LAZY (luồng có thể vô hạn).

    Hai phần tử bằng nhau: phần tử của luồng đứng trước ra trước. Không dùng heapq.merge.
    """
    heap = []
    for index, stream in enumerate(streams):
        it = iter(stream)
        for first in it:                     # lấy phần tử đầu nếu có
            heap.append((first, index, it))
            break
    heapq.heapify(heap)
    while heap:
        value, index, it = heap[0]
        yield value
        for nxt in it:
            heapq.heapreplace(heap, (nxt, index, it))   # chỉ số luồng phá hoà -> ổn định, không so iterator
            break
        else:
            heapq.heappop(heap)
