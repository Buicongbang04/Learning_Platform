"""Chấm weekly_report.xlsx: bảng Weekly, các ô Checks và ghi chú. Nội dung ghi chú chấm thêm theo rubric."""

import re
from collections import defaultdict
from datetime import datetime, timedelta

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BOOK = "weekly_report.xlsx"
FIRST, LAST = 2, 6730
WEEKS = {k + 2: datetime(2011, 10, 31) + timedelta(days=7 * k) for k in range(5)}   # hàng Weekly -> thứ Hai


def norm(formula):
    return re.sub(r"_XLFN\.|_XLWS\.|COM\.MICROSOFT\.", "", (formula or "").upper())


def need_formula(wb, sheet, cell):
    f = wb.formula(sheet, cell)
    if f is None:
        pytest.fail(f"{sheet}!{cell} chưa có công thức: ô đang trống hoặc gõ cứng giá trị. Điền công thức bắt đầu bằng =")
    return norm(f)


@pytest.fixture(scope="module")
def wb():
    return ex.workbook(BOOK)


@pytest.fixture(scope="module")
def truth(wb):
    """Tính lại từ 8 cột gốc của sheet Data theo định nghĩa chung."""
    rev, orders, custs = defaultdict(float), defaultdict(set), defaultdict(set)
    all_custs, seen, dup, excluded = set(), set(), 0, 0
    for r in range(FIRST, LAST + 1):
        row = tuple(wb.value("Data", f"{c}{r}") for c in "ABCDEFGH")
        inv, _, _, qty, date, price, cust, _ = row
        dup += row in seen
        seen.add(row)
        week = datetime(date.year, date.month, date.day) - timedelta(days=date.weekday())
        if str(inv).startswith("C") or qty <= 0 or price <= 0:
            excluded += 1
            continue
        rev[week] += qty * price
        orders[week].add(str(inv))
        if cust is not None:
            custs[week].add(cust)
            all_custs.add(cust)
    return {"rev": rev, "orders": {k: len(v) for k, v in orders.items()}, "custs": {k: len(v) for k, v in custs.items()},
            "all_custs": len(all_custs), "dup": dup, "excluded": excluded}


def test_weekly_tung_tuan(wb, truth):
    for row, week in WEEKS.items():
        for col in "BCDE":
            need_formula(wb, "Weekly", f"{col}{row}")
        assert wb.value("Weekly", f"B{row}") == pytest.approx(truth["rev"][week]), f"Weekly!B{row} doanh thu tuần {week:%d/%m}"
        assert wb.value("Weekly", f"C{row}") == truth["orders"][week], f"Weekly!C{row} số đơn tuần {week:%d/%m}"
        assert wb.value("Weekly", f"D{row}") == truth["custs"][week], f"Weekly!D{row} số khách tuần {week:%d/%m}"
        assert wb.value("Weekly", f"E{row}") == pytest.approx(truth["rev"][week] / truth["orders"][week]), f"Weekly!E{row}"
        if row > 2:
            need_formula(wb, "Weekly", f"F{row}")
            prev = WEEKS[row - 1]
            assert wb.value("Weekly", f"F{row}") == pytest.approx(truth["rev"][week] / truth["rev"][prev] - 1), f"Weekly!F{row}"
    assert wb.value("Weekly", "F2") in (None, ""), "F2 để trống: tuần đầu không có tuần trước trong dữ liệu"


def test_weekly_dong_tong(wb, truth):
    assert sum(truth["rev"].values()) == pytest.approx(198855.47, abs=0.01)
    assert (sum(truth["orders"].values()), truth["all_custs"], truth["excluded"], truth["dup"]) == (314, 176, 209, 24)
    for col in "BCDE":
        need_formula(wb, "Weekly", f"{col}7")
    assert wb.value("Weekly", "B7") == pytest.approx(sum(truth["rev"].values()))
    assert wb.value("Weekly", "C7") == sum(truth["orders"].values())
    assert wb.value("Weekly", "D7") == truth["all_custs"], (
        "D7 là số khách khác nhau trong 5 tuần; cộng số khách từng tuần sẽ đếm một khách nhiều lần "
        f"({sum(truth['custs'].values())} thay vì {truth['all_custs']})")
    assert wb.value("Weekly", "E7") == pytest.approx(wb.value("Weekly", "B7") / wb.value("Weekly", "C7"))


def test_checks(wb, truth):
    formulas = {cell: need_formula(wb, "Checks", cell) for cell in ["B2", "B3", "B4", "B5", "B6", "B7"]}
    for cell in ["B2", "B3"]:
        assert "WEEKLY!" in formulas[cell], f"Checks!{cell} phải so số trên sheet Weekly với dữ liệu gốc, không so số gõ tay"
    for cell in ["B2", "B3", "B4", "B7"]:
        assert wb.value("Checks", cell) is True, f"Checks!{cell} phải ra TRUE trên báo cáo đúng"
    assert wb.value("Checks", "B5") == truth["excluded"]
    assert wb.value("Checks", "B6") == truth["dup"]
    assert "AND" in formulas["B7"], "Checks!B7 gộp các kiểm tra bằng AND"


def test_ghi_chu(wb):
    text = wb.value("Notes", "A2") or ""
    assert len(text.split()) >= 40, "Notes!A2: viết ghi chú 3–6 câu (ít nhất 40 từ)"
    assert re.search(r"\d", text), "Ghi chú phải có số liệu"
