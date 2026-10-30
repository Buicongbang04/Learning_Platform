import csv
import math

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def cap():
    return ex.module("capacity.py")


@pytest.fixture(scope="module")
def bench():
    # Benchmark GIẢ ĐỊNH (model 7B, một GPU), cùng dạng số mà `vllm bench serve` in ra; không phải số đo thật.
    with open(ex.fixtures / "bench_7b_1gpu.csv") as f:
        return [{"concurrency": int(r["concurrency"]), "ttft_p95_s": float(r["ttft_p95_s"]),
                 "tpot_p95_s": float(r["tpot_p95_s"])} for r in csv.DictReader(f)]


def row(bench, c):
    return next(r for r in bench if r["concurrency"] == c)


def test_peak_rps(cap):
    # 432 000 request/ngày = 5 rps trung bình; giờ cao điểm gấp 4 lần trung bình
    assert cap.peak_rps(432_000, 4) == pytest.approx(20.0)
    assert cap.peak_rps(864_000, 1) == pytest.approx(10.0)
    with pytest.raises(ValueError):
        cap.peak_rps(1000, 0.5)  # cao điểm không thể thấp hơn trung bình


def test_little(cap):
    # 20 request/s, mỗi request 6 s: trung bình 120 request đang chạy cùng lúc
    assert cap.little_concurrency(20, 6) == pytest.approx(120)
    assert cap.little_concurrency(0, 6) == 0
    with pytest.raises(ValueError):
        cap.little_concurrency(-1, 1)


def test_latency_and_throughput(cap, bench):
    assert cap.request_latency(row(bench, 32), 300) == pytest.approx(0.55 + 300 * 0.028)  # 8.95 s
    assert cap.rps_per_gpu(row(bench, 1), 300) == pytest.approx(1 / 3.68)
    assert cap.rps_per_gpu(row(bench, 32), 300) == pytest.approx(32 / 8.95)  # 3.575: batch lớn, mỗi request chậm hơn
    # batch lớn tăng thông lượng dù mỗi request chậm hơn
    assert cap.rps_per_gpu(row(bench, 32), 300) > 10 * cap.rps_per_gpu(row(bench, 1), 300)


def test_best_operating_point(cap, bench):
    # SLO TTFT 1 s, E2E 10 s, 300 token output: c=64 vượt cả hai SLO, c=32 cho thông lượng cao nhất
    assert cap.best_operating_point(bench, 300, 1.0, 10.0)["concurrency"] == 32
    # E2E 6 s: chỉ tới c=8 (4.98 s); c=16 là 6.3 s
    assert cap.best_operating_point(bench, 300, 1.0, 6.0)["concurrency"] == 8
    # TTFT 0.25 s chặn trước E2E
    assert cap.best_operating_point(bench, 300, 0.25, 60.0)["concurrency"] == 8
    # không gì đạt
    assert cap.best_operating_point(bench, 300, 1.0, 3.0) is None


def test_best_point_is_max_throughput_not_max_concurrency(cap):
    # c=8 vẫn đạt SLO nhưng chậm tới mức thông lượng thấp hơn c=4
    bench = [{"concurrency": 4, "ttft_p95_s": 0.1, "tpot_p95_s": 0.01},
             {"concurrency": 8, "ttft_p95_s": 0.1, "tpot_p95_s": 0.03}]
    assert cap.best_operating_point(bench, 100, 1.0, 10.0)["concurrency"] == 4


def test_gpus_needed(cap, bench):
    # 20 rps * 1.2 / 3.575 = 6.71 -> 7, cộng 1 dự phòng
    assert cap.gpus_needed(20, bench, 300, 1.0, 10.0) == 8
    # SLO E2E chặt hơn (6 s): 24 / 1.606 = 14.94 -> 15 + 1. Gần gấp đôi GPU.
    assert cap.gpus_needed(20, bench, 300, 1.0, 6.0) == 16
    assert cap.gpus_needed(20, bench, 300, 1.0, 10.0, headroom=0, redundancy=0) == 6  # 5.59 -> 6
    # đúng biên không được làm tròn lên thêm một GPU
    flat = [{"concurrency": 10, "ttft_p95_s": 0.0, "tpot_p95_s": 0.01}]  # 10 / 1 s = 10 rps mỗi GPU
    assert cap.gpus_needed(30, flat, 100, 1.0, 2.0, headroom=0, redundancy=0) == 3
    assert isinstance(cap.gpus_needed(20, bench, 300, 1.0, 10.0), int)
    with pytest.raises(ValueError):
        cap.gpus_needed(20, bench, 300, 1.0, 3.0)


def test_costs_and_break_even(cap):
    # 8 GPU, giá thuê GIẢ ĐỊNH 1.20 USD/giờ, 730 giờ/tháng
    assert cap.self_host_monthly_usd(8, 1.2) == pytest.approx(7008.0)
    assert cap.self_host_monthly_usd(8, 1.2, hours_per_month=720) == pytest.approx(6912.0)
    # API 0.0035 USD/request: hoà vốn ở ~2.0 triệu request/tháng
    assert cap.break_even_requests_per_month(7008.0, 0.0035) == pytest.approx(2_002_285.714, abs=1e-2)
    # self-host còn tốn điện/băng thông 0.0005 USD/request: hoà vốn xa hơn
    assert cap.break_even_requests_per_month(7008.0, 0.0035, 0.0005) == pytest.approx(2_336_000.0)
    assert cap.break_even_requests_per_month(7008.0, 0.0005, 0.0005) == math.inf
