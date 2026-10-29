"""Lời giải. Load test tối giản cho một API HTTP: bắn N request với C luồng đồng thời, đo p50/p95/p99,
throughput, error rate và so với SLO.

Chạy tay (sau khi làm xong), ví dụ với API metric của module 09 đang chạy ở cổng 8000:
    uv run python loadtest.py "http://127.0.0.1:8000/daily_sales?start=2018-01-01&end=2018-01-31" 200 10
"""

from __future__ import annotations

import asyncio
import math
import sys
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Result:
    """Kết quả một request. status=None khi không có response (timeout, không kết nối được)."""

    status: int | None
    latency_s: float
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 400


@dataclass(frozen=True)
class SLO:
    """Mục tiêu dịch vụ: p95 không vượt p95_ms, tỉ lệ lỗi không vượt max_error_rate,
    throughput không dưới min_throughput_rps."""

    p95_ms: float
    max_error_rate: float
    min_throughput_rps: float = 0.0


def percentile(values: list[float], q: float) -> float:
    """Percentile theo nearest-rank: sắp xếp tăng dần, lấy phần tử thứ ceil(q/100 * n) (đếm từ 1).

    q = 0 trả phần tử nhỏ nhất. values rỗng hoặc q ngoài [0, 100] thì raise ValueError.
    """
    if not values:
        raise ValueError("values rỗng")
    if not 0 <= q <= 100:
        raise ValueError("q phải trong [0, 100]")
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return ordered[rank - 1]


def summarize(results: list[Result], wall_time_s: float) -> dict:
    """Tổng hợp kết quả. Trả dict có đúng các khoá:

    requests, errors (số result không ok), error_rate (errors / requests),
    throughput_rps (requests / wall_time_s), p50_ms, p95_ms, p99_ms, max_ms
    (latency tính trên MỌI request, kể cả request lỗi, đơn vị mili giây).
    results rỗng thì raise ValueError.
    """
    if not results:
        raise ValueError("không có request nào để tổng hợp")
    n = len(results)
    errors = sum(1 for r in results if not r.ok)
    latencies_ms = [r.latency_s * 1000 for r in results]
    return {
        "requests": n,
        "errors": errors,
        "error_rate": errors / n,
        "throughput_rps": n / wall_time_s,
        "p50_ms": percentile(latencies_ms, 50),
        "p95_ms": percentile(latencies_ms, 95),
        "p99_ms": percentile(latencies_ms, 99),
        "max_ms": max(latencies_ms),
    }


def check_slo(summary: dict, slo: SLO) -> list[str]:
    """Danh sách tên chỉ tiêu vi phạm, theo thứ tự "p95_ms", "error_rate", "throughput_rps".

    Vi phạm khi p95_ms > slo.p95_ms, error_rate > slo.max_error_rate,
    throughput_rps < slo.min_throughput_rps. Bằng đúng ngưỡng là đạt.
    """
    violations = []
    if summary["p95_ms"] > slo.p95_ms:
        violations.append("p95_ms")
    if summary["error_rate"] > slo.max_error_rate:
        violations.append("error_rate")
    if summary["throughput_rps"] < slo.min_throughput_rps:
        violations.append("throughput_rps")
    return violations


async def run_load(
    url: str, *, total_requests: int, concurrency: int, timeout_s: float = 2.0
) -> tuple[list[Result], float]:
    """Gửi total_requests request GET tới url, không bao giờ quá `concurrency` request cùng lúc.

    - Dùng một httpx.AsyncClient(timeout=timeout_s) cho cả lần chạy.
    - Latency mỗi request đo bằng time.perf_counter() quanh lời gọi.
    - Có response (kể cả 4xx/5xx): Result(status=mã, latency_s=...).
    - httpx.HTTPError (timeout, không kết nối được...): Result(status=None, latency_s=...,
      error=tên lớp exception). Không để exception làm dừng cả lần chạy.
    Trả (danh sách result, wall time tính bằng giây từ lúc bắt đầu tới khi request cuối xong).
    """
    results: list[Result] = []
    remaining = iter(range(total_requests))      # các worker chia nhau lấy "vé" request

    async def one(client: httpx.AsyncClient) -> Result:
        start = time.perf_counter()
        try:
            resp = await client.get(url)
            return Result(status=resp.status_code, latency_s=time.perf_counter() - start)
        except httpx.HTTPError as exc:
            return Result(status=None, latency_s=time.perf_counter() - start, error=type(exc).__name__)

    async def worker(client: httpx.AsyncClient) -> None:
        for _ in remaining:                       # mỗi worker một request tại một thời điểm
            results.append(await one(client))

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=timeout_s, limits=limits) as client:
        started = time.perf_counter()
        await asyncio.gather(*(worker(client) for _ in range(min(concurrency, total_requests))))
        wall = time.perf_counter() - started
    return results, wall


def load_test(url: str, *, total_requests: int, concurrency: int, slo: SLO, timeout_s: float = 2.0) -> dict:
    """Chạy run_load (asyncio.run), summarize, check_slo.

    Trả summary cộng thêm hai khoá: "violations" (kết quả check_slo) và "passed" (True khi không vi phạm).
    """
    results, wall = asyncio.run(
        run_load(url, total_requests=total_requests, concurrency=concurrency, timeout_s=timeout_s)
    )
    report = summarize(results, wall)
    report["violations"] = check_slo(report, slo)
    report["passed"] = not report["violations"]
    return report


if __name__ == "__main__":
    target, n, c = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    report = load_test(target, total_requests=n, concurrency=c, slo=SLO(p95_ms=500, max_error_rate=0.01))
    for key, value in report.items():
        print(f"{key:>15}: {value}")
    sys.exit(0 if report["passed"] else 1)
