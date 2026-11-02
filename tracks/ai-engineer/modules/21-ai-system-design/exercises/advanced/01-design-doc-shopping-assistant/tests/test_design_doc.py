import re

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)

HEADINGS = [
    "## 1. Bối cảnh và phạm vi",
    "## 2. Yêu cầu và chỉ số thành công",
    "## 3. Ước lượng",
    "## 4. Chọn kiến trúc",
    "## 5. Kiến trúc tổng thể",
    "## 6. Thiết kế chi tiết",
    "## 7. Đánh giá và vận hành",
    "## 8. An toàn và quyền riêng tư",
    "## 9. Rủi ro và đánh đổi",
    "## 10. Lộ trình triển khai",
]

# estimate() trên tests/fixtures/assumptions_bank.yaml, tính tay theo định nghĩa trong README bài
EXPECTED = {
    "requests_per_day": 600_000,  # 150 000 * 4
    "peak_rps": 600_000 / 86_400 * 3,  # 20.83
    "peak_concurrency": 600_000 / 86_400 * 3 * 5.0,  # Little: 104.2
    "api_cost_per_request": (1000 * 2.0 + 2000 * 0.2 + 200 * 10.0) / 1e6,  # 0.0044
    "api_cost_per_1k": 4.4,
    "api_monthly_usd": 0.0044 * 600_000 * 30,  # 79 200
    "weights_gib": 7.6e9 * 4.5 / 8 / 1024**3,  # 3.98
    "kv_kib_per_token": 56.0,  # 2*28*4*128*2 / 1024
    "seqs_per_gpu": 82,  # (22 GiB - 3.98 GiB) / (56 KiB * 4096)
    "gpus_for_memory": 2,
    "gpus_for_throughput": 8,  # ceil(20.83 * 1.2 / 3.5)
    "gpus": 8,
    "self_host_monthly_usd": 8 * 0.8 * 730,  # 4 672
}

TABLE = """| Chỉ số | Giá trị |
| --- | --- |
| requests_per_day | 600,000 |
| peak_rps | 20.83 |
| peak_concurrency | 104.17 |
| api_cost_per_request | 0.004400 |
| api_cost_per_1k | 4.40 |
| api_monthly_usd | 79,200.00 |
| weights_gib | 3.98 |
| kv_kib_per_token | 56.00 |
| seqs_per_gpu | 82 |
| gpus_for_memory | 2 |
| gpus_for_throughput | 8 |
| gpus | 8 |
| self_host_monthly_usd | 4,672.00 |
"""


def fixture_assumptions():
    return yaml.safe_load((ex.fixtures / "assumptions_bank.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def est():
    return ex.module("estimates.py")


def test_estimate_on_fixture(est):
    got = est.estimate(fixture_assumptions())
    assert set(got) == set(EXPECTED)
    for key, value in EXPECTED.items():
        assert got[key] == pytest.approx(value, rel=1e-9), key
    for key in ("requests_per_day", "seqs_per_gpu", "gpus_for_memory", "gpus_for_throughput", "gpus"):
        assert isinstance(got[key], int), key


def test_estimate_without_cache_and_bad_input(est):
    a = fixture_assumptions()
    del a["request"]["cached_input_tokens"]
    assert est.estimate(a)["api_cost_per_request"] == pytest.approx((3000 * 2.0 + 200 * 10.0) / 1e6)
    a = fixture_assumptions()
    a["request"]["cached_input_tokens"] = 4000
    with pytest.raises(ValueError):
        est.estimate(a)
    a = fixture_assumptions()
    a["self_host"]["vram_gib"] = 4  # 3.98 GiB trọng số + 2 GiB dự phòng không vừa 4 GiB
    with pytest.raises(ValueError):
        est.estimate(a)


def test_render_table(est):
    assert est.render_table(est.estimate(fixture_assumptions())) == TABLE


def test_design_doc():
    doc = ex.read("DESIGN.md")
    assert "TODO" not in doc, "còn TODO trong DESIGN.md"
    for h in HEADINGS:
        assert re.search(rf"^{re.escape(h)}", doc, re.M), f"thiếu mục: {h}"
    assert len(doc.split()) >= 1500, f"DESIGN.md mới có {len(doc.split())} từ (cần >= 1500)"
    assert doc.count("```mermaid") >= 2, "cần ít nhất 2 sơ đồ mermaid"
    est = ex.module("estimates.py")
    assumptions = yaml.safe_load(ex.read("assumptions.yaml"))
    table = est.render_table(est.estimate(assumptions))
    assert table.strip() in doc, "bảng ước lượng trong DESIGN.md phải đúng bằng render_table(estimate(assumptions.yaml))"
