"""Chấm customer_recency.xlsx: MINIFS/MAXIFS/COUNTIFS/SUMIFS theo khách, DATEDIF, segment IF,
Data Validation ở L4 và Conditional Formatting trên cột Segment."""

import re
from datetime import datetime

import openpyxl
import pytest
from openpyxl.utils import range_boundaries

from testkit import Exercise

ex = Exercise(__file__)
BOOK = "customer_recency.xlsx"
FIRST, LAST = 2, 121          # sheet Customers
INV_LAST = 856                # sheet Invoices
REPORT_DATE = datetime(2011, 12, 10)
FAMILIES = {"B": ("MINIFS",), "C": ("MAXIFS",), "D": ("COUNTIFS",), "E": ("SUMIFS",), "F": ("DATEDIF",),
            "G": ("DATEDIF",), "H": ("IF",)}


def norm(formula):
    return re.sub(r"_XLFN\.|_XLWS\.|COM\.MICROSOFT\.", "", (formula or "").upper())


def need_formula(wb, sheet, cell, *families):
    f = wb.formula(sheet, cell)
    if f is None:
        pytest.fail(f"{sheet}!{cell} chưa có công thức: ô đang trống hoặc gõ cứng giá trị. Điền công thức bắt đầu bằng =")
    for options in families:
        if not any(name in norm(f) for name in options):
            pytest.fail(f"{sheet}!{cell} = {f}: bài này yêu cầu dùng {' hoặc '.join(options)}")


def months_between(a: datetime, b: datetime) -> int:
    """DATEDIF(a, b, "m"): số tháng TRÒN, chưa tới ngày trong tháng thì chưa tính."""
    return (b.year - a.year) * 12 + b.month - a.month - (b.day < a.day)


def covers(coord: str, col: int, row: int) -> bool:
    min_col, min_row, max_col, max_row = range_boundaries(coord)
    return min_col <= col <= max_col and min_row <= row <= max_row


def segment(days: int) -> str:
    return "Active" if days <= 90 else "At risk" if days <= 180 else "Lost"


@pytest.fixture(scope="module")
def wb():
    return ex.workbook(BOOK)


@pytest.fixture(scope="module")
def expected(wb):
    sales = {}
    for r in range(2, INV_LAST + 1):
        if wb.value("Invoices", f"G{r}") == "Sale":
            sales.setdefault(wb.value("Invoices", f"C{r}"), []).append(
                (wb.value("Invoices", f"B{r}"), wb.value("Invoices", f"F{r}")))
    out = {}
    for r in range(FIRST, LAST + 1):
        rows = sales[wb.value("Customers", f"A{r}")]
        first, last = min(d for d, _ in rows), max(d for d, _ in rows)
        days = (REPORT_DATE - last).days
        out[r] = {"B": first, "C": last, "D": len(rows), "E": sum(t for _, t in rows),
                  "F": months_between(first, last), "G": days, "H": segment(days)}
    return out


def test_cot_khach_la_cong_thuc(wb):
    for r in range(FIRST, LAST + 1):
        for col, fam in FAMILIES.items():
            need_formula(wb, "Customers", f"{col}{r}", fam)
    f = norm(wb.formula("Customers", "G3"))
    assert "$L$1" in f, f"Customers!G3 = {f}: ngày báo cáo phải là tham chiếu tuyệt đối $L$1, kéo xuống không bị trượt"


@pytest.mark.parametrize("col", list(FAMILIES))
def test_gia_tri_tung_cot(wb, expected, col):
    wrong = []
    for r, e in expected.items():
        got = wb.value("Customers", f"{col}{r}")
        ok = got == pytest.approx(e[col]) if isinstance(e[col], float) else got == e[col]
        if not ok:
            wrong.append(f"{col}{r}: được {got!r}, cần {e[col]!r}")
    assert not wrong, f"Cột {col} sai {len(wrong)} ô, ví dụ: " + "; ".join(wrong[:3])


def test_data_validation_va_tra_cuu_segment(wb, expected):
    sheet = openpyxl.load_workbook(wb.path)["Customers"]
    lists = [dv for dv in sheet.data_validations.dataValidation
             if dv.type == "list" and any(covers(rng.coord, 12, 4) for rng in dv.sqref.ranges)]
    assert lists, "Ô L4 chưa có Data Validation dạng danh sách (List)"
    assert lists[0].formula1, "Data Validation của L4 chưa có nguồn danh sách (Active,At risk,Lost hoặc một vùng ô)"
    chosen = wb.value("Customers", "L4")
    assert chosen in ("Active", "At risk", "Lost"), "Chọn một segment ở L4"
    need_formula(wb, "Customers", "L5", ("COUNTIF",))
    need_formula(wb, "Customers", "L6", ("SUMIF",))
    need_formula(wb, "Customers", "L7", ("/", "AVERAGEIF"))
    seg = [e["H"] for e in expected.values()]
    assert (seg.count("Active"), seg.count("At risk"), seg.count("Lost")) == (57, 10, 53)
    assert expected[2]["F"] == 11 and expected[2]["G"] == 37        # khách 12352
    group = [e for e in expected.values() if e["H"] == chosen]
    assert wb.value("Customers", "L5") == len(group)
    assert wb.value("Customers", "L6") == pytest.approx(sum(e["E"] for e in group))
    assert wb.value("Customers", "L7") == pytest.approx(sum(e["E"] for e in group) / len(group))


def test_conditional_formatting_tren_segment(wb):
    sheet = openpyxl.load_workbook(wb.path)["Customers"]
    hits = []
    for cf in sheet.conditional_formatting:
        if any(covers(rng.coord, 8, 60) for rng in cf.sqref.ranges):
            hits.extend(cf.rules)
    assert hits, "Chưa có Conditional Formatting phủ cột Segment (H2:H121)"
    text = " ".join(" ".join(r.formula or []) + " " + (r.text or "") for r in hits)
    assert "Lost" in text or "180" in text, "Quy tắc định dạng nên bắt giá trị Lost (hoặc DaysSinceLast > 180)"
