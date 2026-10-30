"""Chấm ops_report.xlsx sau khi sửa (mọi ô Report đúng, không gõ cứng) và cấu trúc AUDIT.md.
Chất lượng phần giải thích chấm theo rubric trong SOLUTION.md."""

import re
from collections import defaultdict
from datetime import datetime

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BOOK = "ops_report.xlsx"
SEASON = {1: "spring", 2: "summer", 3: "fall", 4: "winter"}       # UCI Readme
MONTH_ROWS = {r: datetime(2011 + (r - 2) // 12, (r - 2) % 12 + 1, 1) for r in range(2, 26)}


def need_formula(wb, sheet, cell):
    f = wb.formula(sheet, cell)
    if f is None:
        pytest.fail(f"{sheet}!{cell} chưa có công thức: ô đang trống hoặc gõ cứng giá trị. Điền công thức bắt đầu bằng =")
    return f.upper()


@pytest.fixture(scope="module")
def wb():
    return ex.workbook(BOOK)


@pytest.fixture(scope="module")
def truth(wb):
    agg = defaultdict(lambda: {"cnt": 0, "casual": 0, "days": 0, "season": None})
    for r in range(2, 733):
        date = wb.value("Days", f"A{r}")
        a = agg[datetime(date.year, date.month, 1)]
        a["cnt"] += wb.value("Days", f"L{r}")
        a["casual"] += wb.value("Days", f"J{r}")
        a["days"] += 1
        if date.day == 1:
            a["season"] = SEASON[wb.value("Days", f"B{r}")]
    return agg


def test_bang_thang(wb, truth):
    wrong = []
    for r, month in MONTH_ROWS.items():
        t = truth[month]
        for col in "BCDEF":
            need_formula(wb, "Report", f"{col}{r}")
        expect = {"B": t["cnt"], "C": t["days"], "D": t["cnt"] / t["days"], "E": t["casual"] / t["cnt"], "F": t["season"]}
        if r >= 14:
            need_formula(wb, "Report", f"G{r}")
            expect["G"] = t["cnt"] / truth[MONTH_ROWS[r - 12]]["cnt"] - 1
        for col, want in expect.items():
            got = wb.value("Report", f"{col}{r}")
            if not (got == want if isinstance(want, str) else isinstance(got, (int, float)) and got == pytest.approx(want)):
                wrong.append(f"{col}{r} ({month:%m/%Y}): được {got!r}, cần {want!r}")
    assert not wrong, f"Report còn {len(wrong)} ô sai, ví dụ: " + "; ".join(wrong[:4])


def test_khong_go_cung_thang_12_2011(wb):
    f = need_formula(wb, "Report", "B13")
    assert "SUMIFS" in f, "Report!B13 phải là SUMIFS như các tháng khác"


def test_dong_tong(wb):
    for cell in ["B27", "B28", "B29", "B30"]:
        need_formula(wb, "Report", cell)
    assert (wb.value("Report", "B27"), wb.value("Report", "B28")) == (1243103, 2049576)
    assert wb.value("Report", "B29") == pytest.approx(2049576 / 366), "B29: tổng lượt 2012 / số ngày 2012, không phải trung bình 12 trung bình tháng"
    assert wb.value("Report", "B30") == pytest.approx(0.6488, abs=1e-4)


def audit_text():
    return ex.read("AUDIT.md")


def test_audit_md():
    text = audit_text()
    assert "TODO" not in text, "AUDIT.md còn TODO"
    for heading in ["## Lỗi đã tìm", "## Headline mới", "## Cách phòng lỗi lần sau"]:
        assert heading in text, f"AUDIT.md thiếu mục {heading}"
    issues = text.split("## Lỗi đã tìm")[1].split("## Headline mới")[0]
    rows = [line for line in issues.splitlines() if line.startswith("|") and not re.match(r"^\|\s*(#|-)", line)]
    assert len(rows) >= 6, f"Bảng lỗi cần ít nhất 6 dòng (đang {len(rows)})"
    for ref in ["B13", "B28", "B29"]:
        assert ref in issues, f"Bảng lỗi chưa nhắc ô {ref}"
    for col in "EFG":
        assert re.search(rf"\b{col}\d+|cột {col}\b", issues), f"Bảng lỗi chưa nhắc lỗi ở cột {col}"
    headline = text.split("## Headline mới")[1].split("## Cách phòng")[0]
    assert re.search(r"\d+([.,]\d+)?\s?%", headline), "Headline mới phải có con số % đã sửa"
