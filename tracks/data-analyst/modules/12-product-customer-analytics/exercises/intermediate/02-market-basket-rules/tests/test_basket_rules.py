import tempfile
import uuid
from pathlib import Path

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
RULE_COLUMNS = ["antecedent", "consequent", "support", "confidence", "lift"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("basket_rules.ipynb")


# Loader Online Retail II của module 12: chép y hệt ở mọi bài dùng bộ này; sửa thì sửa mọi bản.
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"  # cache parquet trong thư mục tạm, không ghi vào data/raw


def read_sheet(sheet: str) -> pd.DataFrame:
    """Một sheet Online Retail II. Lần đầu đọc xlsx (30-90 giây) rồi ghi cache parquet theo mtime và cỡ tệp."""
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_II-{sheet.replace(' ', '_')}-{stat.st_mtime_ns}-{stat.st_size}.parquet"
    if cache.exists():
        try:
            return pd.read_parquet(cache)
        except (OSError, ValueError):  # cache hỏng: đọc lại từ xlsx và ghi đè
            pass
    tx = pd.read_excel(xlsx, sheet_name=sheet)
    tx = tx.assign(Invoice=tx["Invoice"].astype(str), StockCode=tx["StockCode"].astype(str),
                   Description=tx["Description"].astype("string"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{uuid.uuid4().hex}.tmp")  # ghi atomic: tệp tạm rồi đổi tên
    tx.to_parquet(tmp, index=False)
    tmp.replace(cache)
    return tx


def clean_sales(tx: pd.DataFrame) -> pd.DataFrame:
    """Dòng hợp lệ theo định nghĩa dùng chung của track, kèm revenue = Quantity * Price."""
    s = tx.assign(Invoice=tx["Invoice"].astype(str))
    s = s[~s.Invoice.str.startswith("C") & (s.Quantity > 0) & (s.Price > 0)].copy()
    s["revenue"] = s.Quantity * s.Price
    return s


A, B, C, D = "10001", "10002", "10003", "85123A"


def small_lines():
    baskets = {
        "1": [A, B], "2": [A, B, B], "3": [A, B, C], "4": [A, C], "5": [B, C],   # giỏ 2 có B hai dòng
        "6": [C, "POST"], "7": [C, D], "8": [D, "M"], "9": [A, B, D],
        "10": ["POST", "DOT"],                                                   # chỉ có phí: không phải giỏ hàng
    }
    rows = [(inv, code) for inv, codes in baskets.items() for code in codes]
    return pd.DataFrame(rows, columns=["Invoice", "StockCode"])


def test_basket_matrix(nb):
    basket = nb.basket_matrix(small_lines())
    assert basket.shape == (9, 4), "Bỏ mã phí (POST, DOT, M); hoá đơn chỉ có phí không thành giỏ"
    assert sorted(basket.columns) == [A, B, C, D]
    assert (basket.dtypes == bool).all()
    assert basket.loc["2", [A, B, C, D]].tolist() == [True, True, False, False]
    assert int(basket.sum().sum()) == 18, "Một mã xuất hiện hai dòng trong cùng hoá đơn vẫn là một"


def test_basket_matrix_does_not_mutate_input(nb):
    lines = small_lines()
    before = lines.copy()
    nb.basket_matrix(lines)
    pd.testing.assert_frame_equal(lines, before)


def test_rule_stats(nb):
    basket = nb.basket_matrix(small_lines())
    ab = nb.rule_stats(basket, A, B)
    assert ab["support"] == pytest.approx(4 / 9)
    assert ab["confidence"] == pytest.approx(4 / 5)
    assert ab["lift"] == pytest.approx((4 / 9) / ((5 / 9) * (5 / 9)))
    ac = nb.rule_stats(basket, A, C)
    assert ac["lift"] == pytest.approx((2 / 9) / ((5 / 9) * (5 / 9))), "Lift < 1: ít đi cùng hơn ngẫu nhiên"
    cd = nb.rule_stats(basket, C, D)
    dc = nb.rule_stats(basket, D, C)
    assert cd["confidence"] == pytest.approx(1 / 5) and dc["confidence"] == pytest.approx(1 / 3), "Confidence không đối xứng"
    assert cd["lift"] == pytest.approx(dc["lift"]), "Lift đối xứng"


def test_mine_rules(nb):
    basket = nb.basket_matrix(small_lines())
    rules = nb.mine_rules(basket, min_support=0.3)
    assert list(rules.columns) == RULE_COLUMNS
    assert list(zip(rules.antecedent, rules.consequent)) == [(A, B), (B, A)], "Chỉ luật một-một, lift >= 1, sắp lift rồi tên"
    assert rules.support.tolist() == pytest.approx([4 / 9, 4 / 9])
    assert rules.confidence.tolist() == pytest.approx([0.8, 0.8])
    assert rules.lift.tolist() == pytest.approx([1.44, 1.44])
    assert list(rules.index) == [0, 1]


def test_mine_rules_empty(nb):
    basket = nb.basket_matrix(small_lines())
    rules = nb.mine_rules(basket, min_support=0.5)
    assert rules.empty and list(rules.columns) == RULE_COLUMNS, "Không có cặp đủ support: bảng rỗng đúng cột"


def test_stable_rules(nb):
    r1 = pd.DataFrame({"antecedent": ["x", "y", "z"], "consequent": ["y", "x", "w"],
                       "support": [0.1, 0.1, 0.2], "confidence": [0.5, 0.6, 0.7], "lift": [3.0, 3.0, 2.0]})
    r2 = pd.DataFrame({"antecedent": ["y", "z", "q"], "consequent": ["x", "q", "z"],
                       "support": [0.2, 0.1, 0.1], "confidence": [0.4, 0.5, 0.5], "lift": [4.0, 2.5, 2.5]})
    out = nb.stable_rules(r1, r2)
    assert list(zip(out.antecedent, out.consequent)) == [("y", "x")]
    assert out.loc[0, "lift_1"] == pytest.approx(3.0) and out.loc[0, "lift_2"] == pytest.approx(4.0)
    assert {"support_1", "support_2", "confidence_1", "confidence_2"} <= set(out.columns)


@pytest.fixture(scope="module")
def real_sales():
    return clean_sales(read_sheet("Year 2010-2011"))


def test_real_rules(nb, real_sales):
    basket = nb.basket_matrix(real_sales)
    assert basket.shape == (19_773, 3_900)
    assert basket.mean().idxmax() == "85123A"
    rules = nb.mine_rules(basket, min_support=0.02)
    assert len(rules) == 176
    top = rules.iloc[0]
    assert {top.antecedent, top.consequent} == {"22697", "22698"}
    assert top.lift == pytest.approx(16.126, abs=1e-3)
    pink_green = nb.rule_stats(basket, "22698", "22697")
    assert pink_green["confidence"] == pytest.approx(0.8261, abs=1e-4)
    first = nb.mine_rules(nb.basket_matrix(real_sales[real_sales.InvoiceDate < "2011-07-01"]), 0.02)
    second = nb.mine_rules(nb.basket_matrix(real_sales[real_sales.InvoiceDate >= "2011-07-01"]), 0.02)
    assert (len(first), len(second), len(nb.stable_rules(first, second))) == (172, 340, 106)
