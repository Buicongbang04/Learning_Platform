import os
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Trả lời ngắn", "## Độ tập trung doanh thu", "## Đề xuất ngưỡng VIP", "## Rủi ro và giới hạn",
                 "## Việc cần làm"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("concentration.ipynb")


def tiny_tx():
    nan = np.nan
    return pd.DataFrame({
        "Invoice":     [1, 1, "C2", 3, 4, 5, 6, "A7", 8],
        "Quantity":    [2, 1, -5, 10, 1, 3, 4, 1, 2],
        "Price":       [5.0, 10.0, 5.0, 1.0, 0.0, 2.0, 1.0, -50.0, 3.0],
        "Customer ID": [100.0, 100.0, 100.0, 200.0, 200.0, nan, 300.0, 300.0, 100.0],
    })


def test_customer_revenue(nb):
    tx = tiny_tx()
    before = tx.copy()
    out = nb.customer_revenue(tx)
    pd.testing.assert_frame_equal(tx, before)
    # 100: 10 + 10 + 6 = 26 (bỏ C2); 200: 10 (bỏ dòng giá 0); 300: 4 (bỏ A7 giá âm); khách trống bị bỏ
    assert out.to_dict() == {100.0: 26.0, 200.0: 10.0, 300.0: 4.0}
    assert list(out.index) == [100.0, 200.0, 300.0]
    assert out.name == "revenue" and out.index.name == "Customer ID"


def test_lorenz_curve(nb):
    curve = nb.lorenz_curve([30.0, 10.0, 0.0, 60.0])
    assert list(curve.columns) == ["customer_share", "revenue_share"]
    assert curve.customer_share.tolist() == pytest.approx([0, 0.25, 0.5, 0.75, 1.0])
    assert curve.revenue_share.tolist() == pytest.approx([0, 0, 0.1, 0.4, 1.0])


def test_gini(nb):
    assert nb.gini([5.0, 5.0, 5.0, 5.0]) == pytest.approx(0.0)
    assert nb.gini([0.0, 0.0, 0.0, 8.0]) == pytest.approx(0.75)               # (n - 1) / n
    x = pd.Series([1.0, 2.0, 3.0, 4.0])
    assert nb.gini(x) == pytest.approx(0.25)
    assert nb.gini(x * 1000) == pytest.approx(0.25)                             # không phụ thuộc đơn vị
    assert isinstance(nb.gini(x), float)


def test_gini_matches_lorenz_area(nb):
    rng = np.random.default_rng(7)
    x = rng.lognormal(6, 1.5, 500)
    curve = nb.lorenz_curve(x)
    area = np.trapezoid(curve.revenue_share, curve.customer_share)
    assert nb.gini(x) == pytest.approx(1 - 2 * area, abs=1e-9)


def test_top_share(nb):
    x = [50.0, 10.0, 30.0, 5.0, 5.0]
    assert nb.top_share(x, 0.2) == pytest.approx(0.5)                          # ceil(1) = 1 giá trị lớn nhất
    assert nb.top_share(x, 0.3) == pytest.approx(0.8)                          # ceil(1.5) = 2
    assert nb.top_share(x, 1.0) == pytest.approx(1.0)
    assert nb.top_share(np.full(10, 3.0), 0.2) == pytest.approx(0.2)           # 0.2 * 10 không bị làm tròn lên 3


@pytest.mark.parametrize("bad", [[], [1.0, np.nan], [1.0, -1.0], [0.0, 0.0]])
def test_reject_bad_values(nb, bad):
    for call in (lambda: nb.gini(bad), lambda: nb.lorenz_curve(bad), lambda: nb.top_share(bad, 0.5)):
        with pytest.raises(ValueError):
            call()


def test_top_share_rejects_bad_q(nb):
    for q in (0.0, 1.5, -0.1):
        with pytest.raises(ValueError):
            nb.top_share([1.0, 2.0], q)


def read_retail_1011() -> pd.DataFrame:
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    stat = xlsx.stat()
    cache = Path(tempfile.gettempdir()) / "da-cache" / f"retail-1011-{stat.st_size}-{int(stat.st_mtime)}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = pd.read_excel(xlsx, sheet_name="Year 2010-2011")                     # lần đầu 20-90 giây
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    df["Description"] = df["Description"].astype("string")
    cache.parent.mkdir(exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
    df.to_parquet(tmp)
    tmp.replace(cache)
    return df


def test_real_concentration(nb):
    rev = nb.customer_revenue(read_retail_1011())
    assert len(rev) == 4338
    assert rev.sum() == pytest.approx(8_911_425.90, abs=0.01)
    assert rev.index[0] == 14646.0
    assert nb.gini(rev) == pytest.approx(0.7151, abs=1e-4)
    assert nb.top_share(rev, 0.2) == pytest.approx(0.7462, abs=1e-4)
    assert nb.top_share(rev, 0.01) == pytest.approx(0.3200, abs=1e-4)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo hai phút: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
