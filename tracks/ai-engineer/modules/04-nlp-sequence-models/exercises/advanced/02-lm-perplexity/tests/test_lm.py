import math
import re

import pytest
import torch
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("lm.ipynb")


def test_batchify(nb):
    data = nb.batchify(list(range(23)), 4)
    assert data.dtype == torch.long and data.shape == (4, 5)
    assert data[0].tolist() == [0, 1, 2, 3, 4] and data[1].tolist() == [5, 6, 7, 8, 9], \
        "dòng b là đoạn LIÊN TỤC thứ b của chuỗi (không xen kẽ)"
    assert data[3].tolist() == [15, 16, 17, 18, 19], "bỏ phần dư 20, 21, 22"


def test_get_batch(nb):
    data = nb.batchify(list(range(40)), 2)          # 2 dòng × 20
    x, y = nb.get_batch(data, 0, 8)
    assert x.shape == (2, 8) and x[0].tolist() == list(range(8)) and y[0].tolist() == list(range(1, 9))
    x, y = nb.get_batch(data, 16, 8)
    assert x.shape == (2, 3), "đoạn cuối ngắn hơn: L = min(bptt, n - 1 - i)"
    assert x[1].tolist() == [36, 37, 38] and y[1].tolist() == [37, 38, 39]


def test_nll_to_metrics(nb):
    # 1 000 token, NLL trung bình ln 50 mỗi token, văn bản 4 000 ký tự
    m = nb.nll_to_metrics(1000 * math.log(50), 1000, 4000)
    assert m["ppl"] == pytest.approx(50.0)
    assert m["bits_per_token"] == pytest.approx(math.log2(50))
    assert m["bpc"] == pytest.approx(math.log2(50) / 4), "bpc chia cho số KÝ TỰ, đơn vị bit (log cơ số 2)"


def test_bpc_is_tokenizer_independent(nb):
    # Cùng một văn bản 1 200 ký tự, cùng tổng NLL 900 nat, hai tokenizer cắt khác nhau:
    # perplexity theo token khác hẳn nhau, bpc thì bằng nhau
    coarse = nb.nll_to_metrics(900.0, 300, 1200)
    fine = nb.nll_to_metrics(900.0, 1200, 1200)
    assert coarse["ppl"] == pytest.approx(math.exp(3)) and fine["ppl"] == pytest.approx(math.exp(0.75))
    assert coarse["bpc"] == pytest.approx(fine["bpc"])


def test_sample_next_greedy_and_topk(nb):
    g = torch.Generator().manual_seed(0)
    logits = torch.tensor([1.0, 3.0, 2.0, 0.5])
    assert nb.sample_next(logits, 0.0, None, g) == 1
    draws = [nb.sample_next(logits, 1.0, 2, g) for _ in range(1000)]
    assert set(draws) == {1, 2}, "top_k = 2 chỉ được ra hai token lớn nhất"
    frac = draws.count(1) / 1000
    assert frac == pytest.approx(math.e / (math.e + 1), abs=0.06), "xác suất trong top-k theo softmax"


def test_sample_next_temperature(nb):
    logits = torch.tensor([2.0, 1.0, 0.0])
    g = torch.Generator().manual_seed(1)
    cold = [nb.sample_next(logits, 0.2, None, g) for _ in range(400)]
    hot = [nb.sample_next(logits, 5.0, None, g) for _ in range(2000)]
    assert cold.count(0) / 400 > 0.95
    # T = 5: xác suất 0.40, 0.33, 0.27 (T = 1 thì 0.67, 0.24, 0.09)
    assert hot.count(0) / 2000 < 0.5 and hot.count(2) / 2000 > 0.2, "temperature cao làm phân phối gần đều"
    a = [nb.sample_next(logits, 1.0, None, torch.Generator().manual_seed(7)) for _ in range(5)]
    b = [nb.sample_next(logits, 1.0, None, torch.Generator().manual_seed(7)) for _ in range(5)]
    assert a[0] == b[0], "chỉ dùng generator truyền vào"


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 500, "báo cáo portfolio: ít nhất 500 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng (byte vs BPE)"
    assert re.search(r"bpc|bits?[- ]per[- ]char", doc, re.I), "báo cáo phải dùng bits-per-character"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"
