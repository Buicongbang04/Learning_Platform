"""Chấm revenue_report.xlsx: cột phụ IF ở sheet Data, bảng SUMIFS/COUNTIFS/AOV và khối chỉ số ở sheet Report."""

import re
from collections import defaultdict
from datetime import datetime

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BOOK = "revenue_report.xlsx"
FIRST, LAST = 2, 6811
COUNTRIES = {3: "Germany", 4: "France"}           # hàng của bảng doanh thu; số đơn +5, AOV +10
MONTHS = {"B": 201109, "C": 201110, "D": 201111}


def norm(formula):
    return re.sub(r"_XLFN\.|_XLWS\.|COM\.MICROSOFT\.", "", (formula or "").upper())


def need_formula(wb, sheet, cell, *families):
    f = wb.formula(sheet, cell)
    if f is None:
        pytest.fail(f"{sheet}!{cell} chưa có công thức: ô đang trống hoặc gõ cứng giá trị. Điền công thức bắt đầu bằng =")
    for options in families:
        if not any(name in norm(f) for name in options):
            pytest.fail(f"{sheet}!{cell} = {f}: bài này yêu cầu dùng {' hoặc '.join(options)}")


@pytest.fixture(scope="module")
def wb():
    return ex.workbook(BOOK)


@pytest.fixture(scope="module")
def data(wb):
    rows, prev = {}, "Invoice"
    for r in range(FIRST, LAST + 1):
        inv, qty, date, price, cust, country = (wb.value("Data", f"{c}{r}") for c in "ADEFGH")
        inv = str(inv)
        valid = int(not inv.startswith("C") and qty > 0 and price > 0)
        rows[r] = {"I": valid, "J": qty * price if valid else 0, "K": date.year * 100 + date.month,
                   "L": int(inv != prev and not inv.startswith("C")), "country": country, "date": date, "cust": cust}
        prev = inv
    return rows


def test_cot_phu_la_cong_thuc(wb):
    for r in range(FIRST, LAST + 1):
        need_formula(wb, "Data", f"I{r}", ("IF",))
        need_formula(wb, "Data", f"J{r}", ("IF", "*"))
        need_formula(wb, "Data", f"K{r}", ("YEAR",), ("MONTH",))
        need_formula(wb, "Data", f"L{r}", ("IF",))


@pytest.mark.parametrize("col", ["I", "J", "K", "L"])
def test_gia_tri_cot_phu(wb, data, col):
    wrong = [f"{col}{r}: được {wb.value('Data', f'{col}{r}')!r}, cần {e[col]!r}"
             for r, e in data.items() if wb.value("Data", f"{col}{r}") != pytest.approx(e[col])]
    assert not wrong, f"Cột {col} sai {len(wrong)} ô, ví dụ: " + "; ".join(wrong[:3])


def aggregates(data):
    rev, orders = defaultdict(float), defaultdict(int)
    for e in data.values():
        rev[(e["country"], e["K"])] += e["J"]
        orders[(e["country"], e["K"])] += e["L"]
    return rev, orders


def test_bang_doanh_thu_so_don_aov(wb, data):
    rev, orders = aggregates(data)
    for row, country in COUNTRIES.items():
        for col, month in MONTHS.items():
            need_formula(wb, "Report", f"{col}{row}", ("SUMIFS",))
            need_formula(wb, "Report", f"{col}{row + 5}", ("COUNTIFS",))
            need_formula(wb, "Report", f"{col}{row + 10}", ("/",))
            assert wb.value("Report", f"{col}{row}") == pytest.approx(rev[(country, month)]), f"Report!{col}{row}"
            assert wb.value("Report", f"{col}{row + 5}") == orders[(country, month)], f"Report!{col}{row + 5}"
            assert wb.value("Report", f"{col}{row + 10}") == pytest.approx(rev[(country, month)] / orders[(country, month)])
    for cell in ["E3", "E4", "B5", "C5", "D5", "E5", "E8", "E9", "B10", "C10", "D10", "E10", "B15", "C15", "D15", "E15", "E13", "E14"]:
        need_formula(wb, "Report", cell, ("SUM", "/"))
    total_rev, total_orders = sum(rev.values()), sum(orders.values())
    assert wb.value("Report", "E5") == pytest.approx(total_rev) and total_rev == pytest.approx(166426.86)
    assert wb.value("Report", "E10") == total_orders == 311
    assert wb.value("Report", "E15") == pytest.approx(total_rev / total_orders), "E15 là tổng doanh thu / tổng số đơn, không phải trung bình các AOV"
    assert wb.value("Report", "C14") == pytest.approx(956.727, abs=1e-3)


def test_khoi_chi_so(wb, data):
    families = {"H2": ("COUNTA",), "H3": ("SUM", "COUNTIF"), "H4": ("AVERAGEIF",), "H5": ("MAX",),
                "H6": ("MIN",), "H7": ("MAX",), "H8": ("COUNT",)}
    for cell, fam in families.items():
        need_formula(wb, "Report", cell, fam)
    valid = [e for e in data.values() if e["I"]]
    assert wb.value("Report", "H2") == len(data) == 6810
    assert wb.value("Report", "H3") == len(valid) == 6622
    assert wb.value("Report", "H4") == pytest.approx(sum(e["J"] for e in valid) / len(valid))
    assert wb.value("Report", "H5") == pytest.approx(4161.06)
    assert wb.value("Report", "H6") == datetime(2011, 9, 1, 9, 40)
    assert wb.value("Report", "H7") == datetime(2011, 11, 30, 16, 47)
    assert wb.value("Report", "H8") == sum(e["cust"] is not None for e in data.values()) == 6761
