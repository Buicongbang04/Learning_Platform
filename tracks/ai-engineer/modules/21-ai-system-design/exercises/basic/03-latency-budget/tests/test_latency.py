import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def lat():
    return ex.module("latency.py")


def test_ttft_and_e2e(lat):
    # 2 000 token prompt ở 1 000 tok/s prefill + 0.2 s mạng/hàng đợi
    assert lat.ttft(2000, 1000, overhead_s=0.2) == pytest.approx(2.2)
    assert lat.ttft(2000, 1000) == pytest.approx(2.0)
    # thêm 300 token output ở 30 tok/s: 10 s. Decode chiếm phần lớn độ trễ.
    assert lat.e2e_latency(2000, 300, 1000, 30, overhead_s=0.2) == pytest.approx(12.2)
    assert lat.e2e_latency(0, 0, 1000, 30) == 0.0
    with pytest.raises(ValueError):
        lat.ttft(100, 0)
    with pytest.raises(ValueError):
        lat.e2e_latency(100, 10, 1000, 0)


def test_decode_upper_bound(lat):
    # qwen2.5:3b Q4_K_M (tệp GGUF 1 929 912 432 byte) trên GPU 192 GB/s: tối đa ~99.5 tok/s
    assert lat.decode_upper_bound_tok_s(1_929_912_432, 192e9) == pytest.approx(99.486, abs=1e-3)
    # Qwen2.5-7B bf16 (15.23 GB) trên 360 GB/s: ~23.6 tok/s dù GPU còn dư FLOPs
    assert lat.decode_upper_bound_tok_s(15_231_233_024, 360e9) == pytest.approx(23.636, abs=1e-3)
    with pytest.raises(ValueError):
        lat.decode_upper_bound_tok_s(0, 1e9)


def test_percentile_matches_numpy(lat):
    rng = np.random.default_rng(0)
    for n in (1, 2, 7, 100, 1001):
        xs = rng.lognormal(0, 1, n).tolist()
        for q in (0, 50, 90, 95, 99, 100):
            assert lat.percentile(xs, q) == pytest.approx(float(np.percentile(xs, q)), rel=1e-12)
    assert lat.percentile([3, 1, 2], 50) == 2  # không giả định đầu vào đã sắp xếp
    with pytest.raises(ValueError):
        lat.percentile([], 50)
    with pytest.raises(ValueError):
        lat.percentile([1.0], 101)


def test_pipeline_tails_in_different_requests(lat):
    # đuôi của hai bước rơi vào hai request khác nhau: tổng p80 các bước đánh giá THẤP p80 thật
    stages = {"retrieve": [1, 1, 1, 1, 10], "generate": [10, 1, 1, 1, 1]}
    of_sum, sum_of = lat.pipeline_percentiles(stages, 80)
    assert of_sum == pytest.approx(11.0)
    assert sum_of == pytest.approx(5.6)


def test_pipeline_rare_spikes(lat):
    # 3 bước 0.2 s, mỗi bước 3/100 request bị gai 10 s (ở các request khác nhau). p95 từng bước vẫn 0.2 s
    # nên tổng các p95 = 0.6 s, nhưng 9% request có gai: p95 thật = 10.4 s. Tổng các p95 đánh giá THẤP.
    stages = {}
    for k, s in enumerate(["guard", "retrieve", "llm"]):
        v = [0.2] * 100
        for i in range(3):
            v[10 * k + i] = 10.0
        stages[s] = v
    of_sum, sum_of = lat.pipeline_percentiles(stages, 95)
    assert of_sum == pytest.approx(10.4)
    assert sum_of == pytest.approx(0.6)


def test_pipeline_independent_tails(lat):
    # 3 bước độc lập, đuôi lognormal liên tục: ở đây tổng các p95 đánh giá CAO p95 thật (không phải quy luật chung)
    rng = np.random.default_rng(42)
    stages = {s: rng.lognormal(mu, 0.8, 2000).tolist() for s, mu in [("guard", -3), ("retrieve", -2), ("llm", 0.5)]}
    totals = np.sum([stages[s] for s in stages], axis=0)
    of_sum, sum_of = lat.pipeline_percentiles(stages, 95)
    assert of_sum == pytest.approx(float(np.percentile(totals, 95)), rel=1e-12)
    assert sum_of == pytest.approx(sum(float(np.percentile(v, 95)) for v in stages.values()), rel=1e-12)
    assert sum_of > of_sum


def test_pipeline_rejects_misaligned(lat):
    with pytest.raises(ValueError):
        lat.pipeline_percentiles({"a": [1, 2], "b": [1]}, 50)
    with pytest.raises(ValueError):
        lat.pipeline_percentiles({}, 50)


def test_max_output_tokens(lat):
    # ngân sách 5 s, TTFT 2.2 s, còn 2.8 s * 30 tok/s = 84 token
    assert lat.max_output_tokens(5, 2000, 1000, 30, overhead_s=0.2) == 84
    assert lat.max_output_tokens(2.5, 2000, 1000, 30, overhead_s=0.2) == 9  # đúng biên: 0.3 s * 30, không phải 8
    assert lat.max_output_tokens(2, 2000, 1000, 30, overhead_s=0.2) == 0
    assert isinstance(lat.max_output_tokens(5, 2000, 1000, 30), int)
