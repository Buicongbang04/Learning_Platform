"""Chấm workbook catalog_lookup.xlsx: tra cứu Catalog/Regions bằng công thức, đúng giá trị từng dòng."""

import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BOOK = "catalog_lookup.xlsx"
FIRST, LAST = 2, 1519      # sheet Orders
CAT_LAST = 4102            # sheet Catalog
NOT_FOUND = "NOT IN CATALOG"


def norm(formula):
    return re.sub(r"_XLFN\.|_XLWS\.|COM\.MICROSOFT\.", "", (formula or "").upper())


def need_formula(wb, sheet, cell, *families):
    """families: mỗi phần tử là một bộ tên hàm, công thức phải chứa ít nhất một tên trong mỗi bộ."""
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
def expected(wb):
    catalog = {}
    for r in range(2, CAT_LAST + 1):
        catalog.setdefault(str(wb.value("Catalog", f"B{r}")).upper(),
                           (wb.value("Catalog", f"A{r}"), wb.value("Catalog", f"C{r}")))
    regions, col = {}, 2
    while (name := wb.value("Regions", f"{chr(64 + col)}1")) is not None:
        regions[name] = wb.value("Regions", f"{chr(64 + col)}2")
        col += 1
    out = {}
    for r in range(FIRST, LAST + 1):
        code, qty, price = str(wb.value("Orders", f"D{r}")).upper(), wb.value("Orders", f"E{r}"), wb.value("Orders", f"F{r}")
        desc, lp = catalog.get(code, (NOT_FOUND, None))
        out[r] = {"G": desc, "H": lp, "I": regions[wb.value("Orders", f"C{r}")], "J": qty * price,
                  "K": None if lp is None else 1 - price / lp}
    return out


def test_cot_todo_la_cong_thuc_dung_ho_ham(wb):
    for r in range(FIRST, LAST + 1):
        need_formula(wb, "Orders", f"G{r}", ("XLOOKUP", "INDEX"))
        need_formula(wb, "Orders", f"H{r}", ("VLOOKUP",))
        need_formula(wb, "Orders", f"I{r}", ("HLOOKUP",))
        need_formula(wb, "Orders", f"J{r}", ("*", "PRODUCT"))
        need_formula(wb, "Orders", f"K{r}", ("IF",))


def same(got, want):
    if want is None:
        return got in (None, "")
    if isinstance(want, float):
        return isinstance(got, (int, float)) and got == pytest.approx(want, abs=1e-9)
    return got == want


@pytest.mark.parametrize("col,name", [("G", "Description"), ("H", "ListPrice"), ("I", "Region"),
                                      ("J", "LineValue"), ("K", "DiscountPct")])
def test_gia_tri_tung_cot(wb, expected, col, name):
    wrong = [f"{col}{r}: được {wb.value('Orders', f'{col}{r}')!r}, cần {e[col]!r}"
             for r, e in expected.items() if not same(wb.value("Orders", f"{col}{r}"), e[col])]
    hint = ""
    if col == "H" and wrong:
        hint = " (VLOOKUP thiếu FALSE sẽ tìm gần đúng trên cột chưa sắp xếp và trả giá của mã khác)"
    assert not wrong, f"Cột {name} sai {len(wrong)}/{len(expected)} ô{hint}, ví dụ: " + "; ".join(wrong[:3])


def test_summary(wb, expected):
    need_formula(wb, "Summary", "B2", ("COUNTIF",))
    need_formula(wb, "Summary", "B3", ("COUNTIF",))
    need_formula(wb, "Summary", "B4", ("SUM",))
    need_formula(wb, "Summary", "B5", ("SUMIF",))
    need_formula(wb, "Summary", "B6", ("SUMIF",))
    need_formula(wb, "Summary", "B9", ("INDEX",), ("MATCH",))
    e = expected.values()
    total = sum(x["J"] for x in e)
    assert wb.value("Summary", "B2") == sum(x["G"] == NOT_FOUND for x in e) == 440
    assert wb.value("Summary", "B3") == sum(x["K"] is not None and x["K"] > 1e-9 for x in e) == 260
    assert wb.value("Summary", "B4") == pytest.approx(total) and total == pytest.approx(46188.59)
    assert wb.value("Summary", "B5") == pytest.approx(17297.98, abs=0.01)
    assert wb.value("Summary", "B6") == pytest.approx(0.91136, abs=1e-4)
    assert wb.value("Summary", "B8") == "22423", "Không sửa ô nhập B8"
    assert wb.value("Summary", "B9") == pytest.approx(12.75)
