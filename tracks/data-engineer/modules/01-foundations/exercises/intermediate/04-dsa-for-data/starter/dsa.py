"""DSA cho Data Engineer: hash partitioning, external sort, top-k, Bloom filter, HyperLogLog.

Chỉ dùng thư viện chuẩn. Mọi hàm băm phải ổn định giữa các lần chạy (không dùng hash() của Python,
vì nó đổi theo PYTHONHASHSEED mỗi tiến trình).
"""

from __future__ import annotations

import hashlib
import heapq
import math
from collections.abc import Iterable, Iterator
from pathlib import Path


def hash64(item: str) -> int:
    """Băm chuỗi UTF-8 thành số nguyên 64 bit không dấu, ổn định giữa các máy và các lần chạy."""
    return int.from_bytes(hashlib.blake2b(item.encode("utf-8"), digest_size=8).digest(), "big")


# ---------------------------------------------------------------- 1. hash partitioning


def partition_for(key: str, n_partitions: int) -> int:
    """Trả partition (0..n_partitions-1) của key: hash64(key) % n_partitions.

    n_partitions < 1 thì raise ValueError.
    """
    # TODO 1
    raise NotImplementedError


# ---------------------------------------------------------------- 2. external merge sort


def external_sort(lines: Iterable[str], out_path: Path, *, max_lines: int, tmp_dir: Path) -> int:
    """Sắp xếp tăng dần các dòng (không chứa '\\n') khi chỉ được giữ tối đa max_lines dòng trong RAM.

    Pha 1: đọc lần lượt, mỗi khi buffer đủ max_lines dòng thì sort buffer và ghi thành một tệp run
    trong tmp_dir (UTF-8, mỗi dòng một bản ghi). Phần dư cuối cũng thành một run.
    Pha 2: k-way merge các run (heapq.merge trên các iterator đọc từng dòng) và ghi ra out_path,
    mỗi dòng kết thúc bằng '\\n'. Input rỗng thì out_path là tệp rỗng.
    Xoá các tệp run sau khi merge. Trả số run đã tạo.
    """
    # TODO 2
    raise NotImplementedError


# ---------------------------------------------------------------- 3. top-k bằng heap


def top_k(rows: Iterator[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    """k cặp (key, value) có value lớn nhất trong một stream, chỉ giữ heap tối đa k phần tử.

    Kết quả xếp value giảm dần; cùng value thì key tăng dần. k <= 0 trả [].
    Dùng heapq.heappush / heapq.heappushpop / heapq.heapreplace (gọi qua module heapq).
    """
    # TODO 3
    raise NotImplementedError


# ---------------------------------------------------------------- 4. Bloom filter


class BloomFilter:
    """Tập xấp xỉ: không bao giờ false negative, false positive có thể xảy ra với xác suất kiểm soát được."""

    def __init__(self, m: int, k: int):
        self.m = m
        self.k = k
        self.bits = bytearray(math.ceil(m / 8))

    @staticmethod
    def optimal_params(n: int, p: float) -> tuple[int, int]:
        """(m, k) cho n phần tử và tỉ lệ false positive mục tiêu p.

        m = ceil(-n * ln(p) / (ln 2)^2), k = max(1, round(m / n * ln 2)).
        """
        # TODO 4
        raise NotImplementedError

    @staticmethod
    def expected_fp_rate(m: int, k: int, n: int) -> float:
        """Xác suất false positive lý thuyết sau khi thêm n phần tử: (1 - e^(-k*n/m))^k."""
        # TODO 5
        raise NotImplementedError

    def positions(self, item: str) -> list[int]:
        """k vị trí bit của item bằng double hashing.

        d = blake2b(item UTF-8, digest_size=16); h1 = 8 byte đầu, h2 = 8 byte sau OR 1 (big-endian).
        Vị trí thứ i = (h1 + i * h2) % m, i = 0..k-1.
        """
        # TODO 6
        raise NotImplementedError

    def add(self, item: str) -> None:
        """Bật k bit của item (bit p nằm ở byte p // 8, mặt nạ 1 << (p % 8))."""
        # TODO 7
        raise NotImplementedError

    def __contains__(self, item: str) -> bool:
        # TODO 8: True khi cả k bit đều bật
        raise NotImplementedError


# ---------------------------------------------------------------- 5. HyperLogLog


class HyperLogLog:
    """Đếm xấp xỉ số phần tử phân biệt với m = 2^p register (mỗi register một byte)."""

    def __init__(self, p: int = 12):
        if not 4 <= p <= 16:
            raise ValueError("p phải trong 4..16")
        self.p = p
        self.m = 1 << p
        self.registers = bytearray(self.m)

    def add(self, item: str) -> None:
        """x = hash64(item). Index = p bit cao nhất của x. Với w = 64 - p bit còn lại,
        rho = số bit 0 đứng đầu của w (trong độ dài 64 - p) + 1. registers[index] = max(cũ, rho).
        """
        # TODO 9
        raise NotImplementedError

    def count(self) -> int:
        """Ước lượng cardinality, làm tròn số nguyên.

        alpha = 0.7213 / (1 + 1.079 / m); E = alpha * m^2 / sum(2^-M[j]).
        Nếu E <= 2.5 * m và có V register bằng 0 thì dùng linear counting: m * ln(m / V).
        """
        # TODO 10
        raise NotImplementedError

    def merge(self, other: HyperLogLog) -> HyperLogLog:
        """HLL mới đại diện cho hợp hai tập: max từng register. Khác p thì raise ValueError."""
        # TODO 11
        raise NotImplementedError
