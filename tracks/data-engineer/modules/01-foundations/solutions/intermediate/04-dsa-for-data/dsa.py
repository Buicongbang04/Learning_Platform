"""Lời giải: DSA cho Data Engineer (hash partitioning, external sort, top-k, Bloom filter, HyperLogLog)."""

from __future__ import annotations

import hashlib
import heapq
import math
from collections.abc import Iterable, Iterator
from contextlib import ExitStack, closing
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path


def hash64(item: str) -> int:
    """Băm chuỗi UTF-8 thành số nguyên 64 bit không dấu, ổn định giữa các máy và các lần chạy."""
    return int.from_bytes(hashlib.blake2b(item.encode("utf-8"), digest_size=8).digest(), "big")


# ---------------------------------------------------------------- 1. hash partitioning


def partition_for(key: str, n_partitions: int) -> int:
    if n_partitions < 1:
        raise ValueError("n_partitions phải >= 1")
    return hash64(key) % n_partitions


# ---------------------------------------------------------------- 2. external merge sort


def _read_run(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\n")


def external_sort(lines: Iterable[str], out_path: Path, *, max_lines: int, tmp_dir: Path) -> int:
    tmp_dir = Path(tmp_dir)
    it = iter(lines)
    runs: list[Path] = []
    try:
        # Pha 1: cắt input thành các run đã sort, mỗi run tối đa max_lines dòng trong RAM.
        while chunk := list(islice(it, max_lines)):
            chunk.sort()
            run = tmp_dir / f"run-{len(runs):05d}.txt"
            run.write_text("".join(f"{line}\n" for line in chunk), encoding="utf-8")
            runs.append(run)

        # Pha 2: k-way merge. heapq.merge chỉ giữ một dòng của mỗi run trong heap.
        with ExitStack() as stack, Path(out_path).open("w", encoding="utf-8") as out:
            readers = [stack.enter_context(closing(_read_run(r))) for r in runs]
            for line in heapq.merge(*readers):
                out.write(line + "\n")
        return len(runs)
    finally:
        for run in runs:
            run.unlink(missing_ok=True)


# ---------------------------------------------------------------- 3. top-k bằng heap


@dataclass(order=True, frozen=True)
class _Ranked:
    """Phần tử heap: nhỏ hơn nghĩa là 'kém hơn' (value nhỏ hơn, hoặc cùng value nhưng key lớn hơn)."""

    value: float
    neg_key: "_ReverseStr"
    key: str = field(compare=False)


@dataclass(frozen=True)
class _ReverseStr:
    s: str

    def __lt__(self, other: "_ReverseStr") -> bool:
        return self.s > other.s


def top_k(rows: Iterator[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    if k <= 0:
        return []
    heap: list[_Ranked] = []                      # min-heap: đỉnh là phần tử kém nhất trong top-k hiện tại
    for key, value in rows:
        item = _Ranked(value, _ReverseStr(key), key)
        if len(heap) < k:
            heapq.heappush(heap, item)
        elif heap[0] < item:
            heapq.heapreplace(heap, item)          # bỏ phần tử kém nhất, thêm phần tử mới
    return [(r.key, r.value) for r in sorted(heap, reverse=True)]


# ---------------------------------------------------------------- 4. Bloom filter


class BloomFilter:
    def __init__(self, m: int, k: int):
        self.m = m
        self.k = k
        self.bits = bytearray(math.ceil(m / 8))

    @staticmethod
    def optimal_params(n: int, p: float) -> tuple[int, int]:
        m = math.ceil(-n * math.log(p) / math.log(2) ** 2)
        k = max(1, round(m / n * math.log(2)))
        return m, k

    @staticmethod
    def expected_fp_rate(m: int, k: int, n: int) -> float:
        return (1 - math.exp(-k * n / m)) ** k

    def positions(self, item: str) -> list[int]:
        d = hashlib.blake2b(item.encode("utf-8"), digest_size=16).digest()
        h1 = int.from_bytes(d[:8], "big")
        h2 = int.from_bytes(d[8:], "big") | 1      # số lẻ để các bước không lặp sớm khi m chẵn
        return [(h1 + i * h2) % self.m for i in range(self.k)]

    def add(self, item: str) -> None:
        for p in self.positions(item):
            self.bits[p >> 3] |= 1 << (p & 7)

    def __contains__(self, item: str) -> bool:
        return all(self.bits[p >> 3] & (1 << (p & 7)) for p in self.positions(item))


# ---------------------------------------------------------------- 5. HyperLogLog


class HyperLogLog:
    def __init__(self, p: int = 12):
        if not 4 <= p <= 16:
            raise ValueError("p phải trong 4..16")
        self.p = p
        self.m = 1 << p
        self.registers = bytearray(self.m)

    def add(self, item: str) -> None:
        x = hash64(item)
        width = 64 - self.p
        idx = x >> width
        w = x & ((1 << width) - 1)
        rho = width - w.bit_length() + 1           # w == 0 cho rho = width + 1
        if rho > self.registers[idx]:
            self.registers[idx] = rho

    def count(self) -> int:
        m = self.m
        alpha = 0.7213 / (1 + 1.079 / m)
        estimate = alpha * m * m / sum(2.0 ** -r for r in self.registers)
        zeros = self.registers.count(0)
        if estimate <= 2.5 * m and zeros:
            estimate = m * math.log(m / zeros)     # linear counting cho cardinality nhỏ
        return round(estimate)

    def merge(self, other: HyperLogLog) -> HyperLogLog:
        if other.p != self.p:
            raise ValueError("Chỉ merge được hai HLL cùng p")
        out = HyperLogLog(self.p)
        out.registers = bytearray(max(a, b) for a, b in zip(self.registers, other.registers))
        return out
