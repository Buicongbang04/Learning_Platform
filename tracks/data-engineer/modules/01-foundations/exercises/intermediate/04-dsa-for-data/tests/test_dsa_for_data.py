"""Chấm bài DSA cho Data Engineer. Dữ liệu sinh trong test với seed cố định, không cần mạng."""

import hashlib
import heapq
import math
import random
from collections import Counter

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def dsa():
    return ex.module("dsa.py")


def _ids(n: int, seed: int, prefix: str = "evt") -> list[str]:
    rng = random.Random(seed)
    return [f"{prefix}-{rng.getrandbits(64):016x}" for _ in range(n)]


# ---------------------------------------------------------------- hash64 và partition_for


def test_hash64_is_stable_blake2b(dsa):
    expected = int.from_bytes(hashlib.blake2b(b"order-42", digest_size=8).digest(), "big")
    assert dsa.hash64("order-42") == expected


def test_partition_for_is_hash_mod_n(dsa):
    for key in ["o1", "o2", "seller-9", "São Paulo"]:
        assert dsa.partition_for(key, 12) == dsa.hash64(key) % 12


def test_partition_for_spreads_keys_evenly(dsa):
    counts = Counter(dsa.partition_for(k, 8) for k in _ids(16_000, seed=1, prefix="order"))
    assert sorted(counts) == list(range(8))
    # kỳ vọng 2000 khoá mỗi partition; hash tốt thì lệch không quá 10%
    assert all(1800 <= c <= 2200 for c in counts.values()), counts


def test_partition_for_rejects_bad_n(dsa):
    with pytest.raises(ValueError):
        dsa.partition_for("o1", 0)


# ---------------------------------------------------------------- external sort


class TrackedLines:
    """Iterable chỉ duyệt được một lần, kiểm tra hàm sort đã ghi run xuống đĩa trước khi đọc tiếp.

    Khi chuẩn bị trả dòng thứ i (đếm từ 0), phải có ít nhất i // max_lines - 1 tệp run trong tmp_dir.
    Hàm nào gom cả input vào RAM rồi mới sort sẽ trượt điều kiện này.
    """

    def __init__(self, lines, tmp_dir, max_lines):
        self.lines = lines
        self.tmp_dir = tmp_dir
        self.max_lines = max_lines
        self.max_files_seen = 0

    def __iter__(self):
        for i, line in enumerate(self.lines):
            files = sum(1 for p in self.tmp_dir.iterdir() if p.is_file())
            self.max_files_seen = max(self.max_files_seen, files)
            need = i // self.max_lines - 1
            assert files >= need, (
                f"Đang đọc dòng {i} nhưng tmp_dir mới có {files} run; "
                f"phải ghi run khi buffer đủ {self.max_lines} dòng"
            )
            yield line


def test_external_sort_orders_lines_with_bounded_memory(dsa, tmp_path):
    lines = _ids(10_000, seed=7, prefix="order")
    lines += lines[:500]                              # có dòng trùng, sort phải giữ đủ
    random.Random(8).shuffle(lines)
    tmp_dir = tmp_path / "runs"
    tmp_dir.mkdir()
    out = tmp_path / "sorted.txt"

    tracked = TrackedLines(lines, tmp_dir, max_lines=1000)
    runs = dsa.external_sort(tracked, out, max_lines=1000, tmp_dir=tmp_dir)

    assert runs == math.ceil(len(lines) / 1000) == 11
    assert tracked.max_files_seen >= 9                # run thật sự nằm trên đĩa trong lúc đọc
    assert out.read_text(encoding="utf-8").splitlines() == sorted(lines)
    assert list(tmp_dir.iterdir()) == []              # dọn tệp run sau khi merge


def test_external_sort_small_and_empty_input(dsa, tmp_path):
    tmp_dir = tmp_path / "runs"
    tmp_dir.mkdir()
    out = tmp_path / "out.txt"
    assert dsa.external_sort(["b", "a", "c"], out, max_lines=10, tmp_dir=tmp_dir) == 1
    assert out.read_text(encoding="utf-8").splitlines() == ["a", "b", "c"]

    assert dsa.external_sort([], out, max_lines=10, tmp_dir=tmp_dir) == 0
    assert out.read_text(encoding="utf-8") == ""


def test_external_sort_unicode(dsa, tmp_path):
    tmp_dir = tmp_path / "runs"
    tmp_dir.mkdir()
    out = tmp_path / "out.txt"
    lines = ["São Paulo", "Rio", "Brasília", "Belém", "Águas"]
    dsa.external_sort(lines, out, max_lines=2, tmp_dir=tmp_dir)
    assert out.read_text(encoding="utf-8").splitlines() == sorted(lines)


# ---------------------------------------------------------------- top-k bằng heap


def test_top_k_matches_full_sort_with_ties(dsa):
    rng = random.Random(3)
    rows = [(f"p{i:05d}", float(rng.randint(1, 500))) for i in range(50_000)]
    expected = sorted(rows, key=lambda r: (-r[1], r[0]))[:10]
    got = dsa.top_k((r for r in rows), 10)            # generator: không được len(), không sort cả stream
    assert got == expected


def test_top_k_keeps_heap_size_k(dsa, monkeypatch):
    sizes = []
    real_push, real_pushpop, real_replace = heapq.heappush, heapq.heappushpop, heapq.heapreplace

    def push(heap, item):
        real_push(heap, item)
        sizes.append(len(heap))

    def pushpop(heap, item):
        out = real_pushpop(heap, item)
        sizes.append(len(heap))
        return out

    def replace(heap, item):
        out = real_replace(heap, item)
        sizes.append(len(heap))
        return out

    monkeypatch.setattr(dsa.heapq, "heappush", push)
    monkeypatch.setattr(dsa.heapq, "heappushpop", pushpop)
    monkeypatch.setattr(dsa.heapq, "heapreplace", replace)
    rows = [(f"p{i}", float(i % 97)) for i in range(5_000)]
    dsa.top_k(iter(rows), 5)
    assert sizes, "gọi heapq.heappush / heapq.heappushpop / heapq.heapreplace qua module heapq"
    assert max(sizes) <= 5


def test_top_k_edge_cases(dsa):
    assert dsa.top_k(iter([]), 3) == []
    assert dsa.top_k(iter([("a", 1.0), ("b", 2.0)]), 5) == [("b", 2.0), ("a", 1.0)]
    assert dsa.top_k(iter([("a", 1.0)]), 0) == []


# ---------------------------------------------------------------- Bloom filter


def test_bloom_optimal_params(dsa):
    assert dsa.BloomFilter.optimal_params(1000, 0.01) == (9586, 7)
    assert dsa.BloomFilter.optimal_params(1_000_000, 0.001) == (14377588, 10)


def test_bloom_expected_fp_rate(dsa):
    assert dsa.BloomFilter.expected_fp_rate(9586, 7, 1000) == pytest.approx(0.01003, abs=1e-4)


def test_bloom_positions_double_hashing(dsa):
    bf = dsa.BloomFilter(m=1000, k=4)
    d = hashlib.blake2b(b"evt-1", digest_size=16).digest()
    h1, h2 = int.from_bytes(d[:8], "big"), int.from_bytes(d[8:], "big") | 1
    assert bf.positions("evt-1") == [(h1 + i * h2) % 1000 for i in range(4)]


def test_bloom_no_false_negative_and_fp_within_bound(dsa):
    m, k = dsa.BloomFilter.optimal_params(5000, 0.01)
    bf = dsa.BloomFilter(m, k)
    members = _ids(5000, seed=11)
    for item in members:
        bf.add(item)
    assert all(item in bf for item in members)        # Bloom filter không bao giờ có false negative

    others = _ids(20_000, seed=12, prefix="new")
    fp = sum(item in bf for item in others) / len(others)
    assert fp <= 0.02, f"tỉ lệ dương tính giả {fp:.4f} vượt 2 lần mục tiêu 1%"


def test_bloom_uses_bitarray_of_m_bits(dsa):
    bf = dsa.BloomFilter(m=10_001, k=3)
    assert isinstance(bf.bits, bytearray)
    assert len(bf.bits) == math.ceil(10_001 / 8)


# ---------------------------------------------------------------- HyperLogLog


def test_hll_rejects_bad_precision(dsa):
    with pytest.raises(ValueError):
        dsa.HyperLogLog(p=3)
    with pytest.raises(ValueError):
        dsa.HyperLogLog(p=17)


def test_hll_registers(dsa):
    hll = dsa.HyperLogLog(p=12)
    assert hll.m == 4096 and len(hll.registers) == 4096
    hll.add("cust-1")
    x = dsa.hash64("cust-1")
    idx = x >> 52
    rest = x & ((1 << 52) - 1)
    rho = 52 - rest.bit_length() + 1
    assert hll.registers[idx] == rho
    assert sum(1 for r in hll.registers if r) == 1


@pytest.mark.parametrize("n", [500, 20_000, 200_000])
def test_hll_estimate_within_error(dsa, n):
    hll = dsa.HyperLogLog(p=12)
    for item in _ids(n, seed=n, prefix="cust"):
        hll.add(item)
    rel_err = abs(hll.count() - n) / n
    assert rel_err <= 3 * 1.04 / math.sqrt(4096), f"n={n}, ước lượng {hll.count()}"


def test_hll_duplicates_and_merge(dsa):
    a, b = dsa.HyperLogLog(p=12), dsa.HyperLogLog(p=12)
    day1 = _ids(30_000, seed=21, prefix="cust")
    day2 = day1[:10_000] + _ids(20_000, seed=22, prefix="cust")   # 10k khách quay lại
    for item in day1:
        a.add(item)
    before = a.count()
    for item in day1[:5000]:
        a.add(item)
    assert a.count() == before                        # thêm phần tử đã có không đổi ước lượng
    for item in day2:
        b.add(item)
    merged = a.merge(b)
    assert merged is not a and merged is not b
    assert abs(merged.count() - 50_000) / 50_000 <= 0.05
    with pytest.raises(ValueError):
        a.merge(dsa.HyperLogLog(p=10))
