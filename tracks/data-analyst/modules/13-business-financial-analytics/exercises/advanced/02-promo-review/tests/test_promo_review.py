import re

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Trả lời ngắn", "## Khuyến mãi tác động bao nhiêu", "## Ở đâu mạnh, ở đâu yếu",
                 "## Điều kiện để có lãi", "## Đề xuất", "## Giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("promo_review.ipynb")


def tiny_train():
    rows = [
        # (Store, DayOfWeek, Sales, Customers, Open, Promo, StoreType)
        (1, 1, 150, 15, 1, 1, "a"), (1, 1, 100, 10, 1, 0, "a"),
        (1, 2, 130, 12, 1, 1, "a"), (1, 2, 100, 10, 1, 0, "a"),
        (2, 1, 300, 20, 1, 1, "b"), (2, 1, 200, 20, 1, 0, "b"),
        (2, 6, 999, 99, 1, 0, "b"),          # thứ Bảy: bỏ
        (2, 3, 0, 0, 0, 1, "b"),             # đóng cửa: bỏ
        (1, 4, 0, 0, 1, 0, "a"),             # mở cửa nhưng không bán: bỏ
    ]
    return pd.DataFrame(rows, columns=["Store", "DayOfWeek", "Sales", "Customers", "Open", "Promo", "StoreType"])


def test_promo_lift_all(nb):
    tr = tiny_train()
    before = tr.copy()
    out = nb.promo_lift(tr)
    pd.testing.assert_frame_equal(tr, before)
    assert list(out.columns) == ["sales_lift", "customers_lift", "spc_lift", "promo_days", "base_days"]
    assert len(out) == 1
    row = out.iloc[0]
    # khuyến mãi: sales TB (150+130+300)/3, khách (15+12+20)/3; thường: 400/3, 40/3
    assert row["sales_lift"] == pytest.approx(580 / 400 - 1)
    assert row["customers_lift"] == pytest.approx(47 / 40 - 1)
    assert row["spc_lift"] == pytest.approx((580 / 47) / (400 / 40) - 1)
    assert (row["promo_days"], row["base_days"]) == (3, 3)


def test_promo_lift_by(nb):
    out = nb.promo_lift(tiny_train(), "StoreType")
    assert out.index.name == "StoreType"
    assert list(out.index) == ["a", "b"]
    assert out.loc["a", "sales_lift"] == pytest.approx(140 / 100 - 1)
    assert out.loc["b", "sales_lift"] == pytest.approx(0.5)
    assert out.loc["b", "customers_lift"] == pytest.approx(0.0)
    assert out.loc["b", "spc_lift"] == pytest.approx(0.5)


def test_breakeven_discount(nb):
    assert nb.breakeven_discount(0.0, 0.3) == pytest.approx(0.0)
    assert nb.breakeven_discount(0.5, 0.4) == pytest.approx(0.4 * 0.5 / (1.5 * 0.6))
    # kiểm bằng định nghĩa: tại d*, lợi nhuận gộp ngày khuyến mãi bằng ngày thường
    lift, m = 0.388, 0.3
    d = nb.breakeven_discount(lift, m)
    s0, s1 = 100.0, 100.0 * (1 + lift)
    assert s1 - (1 - m) * (s1 + d * s1) == pytest.approx(m * s0)


_D = {}


def real(nb):
    if not _D:
        root = ex.dataset("store-sales")
        train = pd.read_csv(root / "train.csv", parse_dates=["Date"], dtype={"StateHoliday": str})
        stores = pd.read_csv(root / "store.csv")
        _D["train"] = train.merge(stores[["Store", "StoreType"]], on="Store", how="left")
    return _D["train"]


def test_real_lift(nb):
    train = real(nb)
    out = nb.promo_lift(train).iloc[0]
    assert out["sales_lift"] == pytest.approx(0.3879, abs=1e-4)
    assert out["customers_lift"] == pytest.approx(0.1977, abs=1e-4)
    assert out["spc_lift"] == pytest.approx(0.1588, abs=1e-4)
    assert (out["promo_days"], out["base_days"]) == (376_875, 319_818)
    by_type = nb.promo_lift(train, "StoreType")
    assert by_type["sales_lift"].idxmin() == "b"
    assert by_type.loc["b", "sales_lift"] == pytest.approx(0.200, abs=1e-3)
    by_day = nb.promo_lift(train, "DayOfWeek")
    assert list(by_day.index) == [1, 2, 3, 4, 5]
    assert by_day["sales_lift"].round(3).tolist() == [0.571, 0.448, 0.368, 0.321, 0.221]
    assert nb.breakeven_discount(out["sales_lift"], 0.30) == pytest.approx(0.1198, abs=1e-4)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo một trang: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
