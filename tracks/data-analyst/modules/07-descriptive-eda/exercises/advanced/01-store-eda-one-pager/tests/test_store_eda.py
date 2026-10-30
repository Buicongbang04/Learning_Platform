import re

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
COLUMNS = ["open_days", "mean_sales", "median_sales", "cv_sales", "sales_per_customer", "promo_lift",
           "StoreType", "Assortment", "CompetitionDistance"]
REPORT_HEADINGS = ["## Câu hỏi", "## Dữ liệu và phạm vi", "## Phát hiện", "### Phát hiện 1", "### Phát hiện 2",
                   "### Phát hiện 3", "## Điều chưa biết", "## Bước tiếp theo"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("store_eda.ipynb")


def tiny():
    train = pd.DataFrame({
        "Store":     [1, 1, 1, 1, 1, 2, 2, 2, 3, 3],
        "Sales":     [100, 200, 300, 0, 50, 400, 400, 0, 90, 110],
        "Customers": [10, 10, 20, 0, 5, 20, 30, 0, 9, 11],
        "Open":      [1, 1, 1, 0, 1, 1, 1, 1, 1, 1],
        "Promo":     [0, 1, 1, 0, 0, 1, 1, 1, 0, 0],
    })
    stores = pd.DataFrame({"Store": [1, 2, 4], "StoreType": ["a", "b", "c"], "Assortment": ["a", "c", "a"],
                           "CompetitionDistance": [500.0, np.nan, 100.0], "Promo2": [0, 1, 0]})
    return train, stores


def test_store_profile_columns_and_index(nb):
    train, stores = tiny()
    out = nb.store_profile(train, stores)
    assert list(out.columns) == COLUMNS
    assert list(out.index) == [1, 2, 3] and out.index.name == "Store"     # cửa hàng 4 không có ngày bán


def test_store_profile_values(nb):
    train, stores = tiny()
    out = nb.store_profile(train, stores)
    s1 = pd.Series([100.0, 200.0, 300.0, 50.0])                              # ngày bán của cửa hàng 1
    assert out.loc[1, "open_days"] == 4
    assert out.loc[1, "mean_sales"] == pytest.approx(162.5)
    assert out.loc[1, "median_sales"] == pytest.approx(150.0)
    assert out.loc[1, "cv_sales"] == pytest.approx(s1.std() / s1.mean())
    assert out.loc[1, "sales_per_customer"] == pytest.approx(650 / 45)
    assert out.loc[1, "promo_lift"] == pytest.approx(250 / 75 - 1)          # promo: 200, 300; không promo: 100, 50
    assert out.loc[2, "open_days"] == 2                                      # dòng mở cửa doanh số 0 bị bỏ
    assert np.isnan(out.loc[2, "promo_lift"]) and np.isnan(out.loc[3, "promo_lift"])
    assert out.loc[1, "StoreType"] == "a" and out.loc[2, "Assortment"] == "c"
    assert np.isnan(out.loc[2, "CompetitionDistance"])
    assert pd.isna(out.loc[3, "StoreType"])                                  # cửa hàng 3 không có trong stores


def test_store_profile_does_not_mutate_input(nb):
    train, stores = tiny()
    before_train, before_stores = train.copy(), stores.copy()
    nb.store_profile(train, stores)
    pd.testing.assert_frame_equal(train, before_train)
    pd.testing.assert_frame_equal(stores, before_stores)


def test_real_store_profile(nb):
    path = ex.dataset("store-sales")
    train = pd.read_csv(path / "train.csv", usecols=["Store", "Sales", "Customers", "Open", "Promo"])
    out = nb.store_profile(train, pd.read_csv(path / "store.csv"))
    assert len(out) == 1115 and out.open_days.sum() == 844_338
    assert out.loc[817, "mean_sales"] == pytest.approx(21757.48, abs=0.01)
    assert out.mean_sales.median() == pytest.approx(6589.95, abs=0.01)
    assert out.cv_sales.median() == pytest.approx(0.2637, abs=1e-4)
    assert out.promo_lift.median() == pytest.approx(0.4056, abs=1e-4)


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report, "Còn dòng TODO trong REPORT.md"
    words = len(report.split())
    assert 250 <= words <= 700, f"Một trang: 250-700 từ, hiện có {words}"
    title = report.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in REPORT_HEADINGS:
        assert heading in report, f"Thiếu mục {heading}"
