import re

import numpy as np
import pytest
import torch
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("interpret_gpt_mini.ipynb")


def test_top_examples_one_per_row(nb):
    acts = torch.tensor([0.0, 5.0, 4.0, -1.0,
                         3.0, 0.0, 0.0, 6.0,
                         0.0, 0.0, 0.0, 0.0,
                         2.0, 2.0, 1.0, 0.0])
    out = nb.top_examples(acts, k=5, row_len=4)
    assert out == [(1, 3, 6.0), (0, 1, 5.0), (3, 0, 2.0)], "mỗi ngữ cảnh một ví dụ, chỉ giá trị dương, hoà lấy chỉ số nhỏ hơn"
    assert all(isinstance(r, int) and isinstance(p, int) and isinstance(v, float) for r, p, v in out)


def test_top_examples_all_and_k(nb):
    acts = torch.tensor([0.5, 5.0, 4.0, 3.0, 6.0, 0.0])
    assert nb.top_examples(acts, k=3, row_len=3, one_per_row=False) == [(1, 1, 6.0), (0, 1, 5.0), (0, 2, 4.0)]
    assert nb.top_examples(acts, k=1, row_len=3) == [(1, 1, 6.0)]
    assert nb.top_examples(torch.zeros(6), k=3, row_len=3) == []


def test_bootstrap_ci_matches_reference(nb):
    values = np.random.default_rng(1).normal(0.3, 1.0, 40)
    lo, hi = nb.bootstrap_ci(values, n_boot=500, alpha=0.1, seed=7)
    idx = np.random.default_rng(7).integers(0, 40, size=(500, 40))
    means = values[idx].mean(axis=1)
    assert lo == pytest.approx(float(np.quantile(means, 0.05)))
    assert hi == pytest.approx(float(np.quantile(means, 0.95)))
    assert isinstance(lo, float) and lo < values.mean() < hi


def test_bootstrap_ci_degenerate_and_width(nb):
    assert nb.bootstrap_ci(np.full(10, 2.5)) == (2.5, 2.5)
    rng = np.random.default_rng(2)
    small = nb.bootstrap_ci(rng.normal(0, 1, 20))
    big = nb.bootstrap_ci(rng.normal(0, 1, 2000))
    assert (big[1] - big[0]) < (small[1] - small[0]) / 4


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 800
    assert re.search(r"^## .*[Kk]ết luận", doc, re.M), "có mục bảng kết luận"
    assert doc.count("|") >= 20, "có bảng"
    for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", doc):
        assert (ex.target / img).exists(), f"thiếu hình {img}"
