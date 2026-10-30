"""Chấm workbook text_cleanup.xlsx: ô TODO phải là công thức đúng họ hàm và cho đúng giá trị."""

import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BOOK = "text_cleanup.xlsx"
FIRST, LAST = 2, 301  # dòng dữ liệu trên sheet Lines
# cột -> (tên, các họ hàm chấp nhận)
COLUMNS = {
    "I": ("StockCode_clean", [("UPPER",), ("TRIM",)]),
    "J": ("Description_clean", [("PROPER",), ("TRIM",)]),
    "K": ("Country_clean", [("SUBSTITUTE",)]),
    "L": ("Line_type", [("IF",), ("LEFT",)]),
    "M": ("Customer_masked", [("REPLACE",)]),
    "N": ("Line_key", [("CONCAT", "&")]),
    "O": ("Slug", [("LOWER",), ("SUBSTITUTE",)]),
    "P": ("Had_extra_spaces", [("TRIM",)]),
}


def norm(formula: str | None) -> str:
    """Bỏ tiền tố LibreOffice/Excel ghi thêm khi lưu (_xlfn.CONCAT, COM.MICROSOFT.…) để so họ hàm."""
    return re.sub(r"_XLFN\.|_XLWS\.|COM\.MICROSOFT\.", "", (formula or "").upper())


def need_formula(wb, sheet: str, cell: str, families) -> None:
    f = wb.formula(sheet, cell)
    if f is None:
        pytest.fail(f"{sheet}!{cell} chưa có công thức: ô đang trống hoặc gõ cứng giá trị. Điền công thức bắt đầu bằng =")
    for options in families:
        if not any(name in norm(f) for name in options):
            pytest.fail(f"{sheet}!{cell} = {f}: bài này yêu cầu dùng {' hoặc '.join(options)}")


def trim(s: str) -> str:
    """TRIM của Excel/LibreOffice: bỏ dấu cách hai đầu và gộp nhiều dấu cách liền nhau thành một."""
    return " ".join(p for p in s.split(" ") if p)


def proper(s: str) -> str:
    """PROPER: chữ cái đứng sau một ký tự không phải chữ cái thì viết hoa, còn lại viết thường."""
    out, prev_alpha = [], False
    for ch in s:
        out.append((ch.lower() if prev_alpha else ch.upper()) if ch.isalpha() else ch)
        prev_alpha = ch.isalpha()
    return "".join(out)


def expected_row(raw: dict) -> dict:
    code, desc, country = raw["B"], raw["C"] or "", raw["H"]
    cust = raw["G"]
    code_clean = trim(str(code)).upper()
    for a, b in [("EIRE", "Ireland"), ("RSA", "South Africa"), ("USA", "United States")]:
        country = country.replace(a, b)
    masked = "Guest" if cust in (None, "") else (lambda s: s[:2] + "**" + s[4:])(str(int(cust)))
    return {
        "I": code_clean,
        "J": proper(trim(desc)),
        "K": country,
        "L": "Cancel" if str(raw["A"]).startswith("C") else "Sale",
        "M": masked,
        "N": f"{raw['A']}-{code_clean}",
        "O": trim(desc).replace(" ", "-").lower(),
        "P": 0 if desc == trim(desc) else 1,
    }


@pytest.fixture(scope="module")
def wb():
    return ex.workbook(BOOK)


@pytest.fixture(scope="module")
def rows(wb):
    return {r: {c: wb.value("Lines", f"{c}{r}") for c in "ABCGH"} for r in range(FIRST, LAST + 1)}


def test_cac_cot_todo_la_cong_thuc(wb):
    for col, (name, families) in COLUMNS.items():
        for r in range(FIRST, LAST + 1):
            need_formula(wb, "Lines", f"{col}{r}", families)


@pytest.mark.parametrize("col", list(COLUMNS))
def test_gia_tri_tung_cot(wb, rows, col):
    name = COLUMNS[col][0]
    wrong = []
    for r, raw in rows.items():
        want, got = expected_row(raw)[col], wb.value("Lines", f"{col}{r}")
        if got is None and want == "":
            continue  # mô tả trống: công thức trả chuỗi rỗng, openpyxl đọc thành None
        if got != want:
            wrong.append(f"{col}{r}: được {got!r}, cần {want!r}")
    assert not wrong, f"Cột {name} sai {len(wrong)} ô, ví dụ: " + "; ".join(wrong[:3])


def test_ca_kho_cua_proper_va_trim(wb):
    # mô tả có hai dấu cách liền nhau + dấu nháy: PROPER viết hoa chữ sau dấu nháy, TRIM gộp dấu cách
    assert trim("ZINC WILLIE WINKIE  CANDLE STICK") == "ZINC WILLIE WINKIE CANDLE STICK"
    assert proper("POPPY'S PLAYHOUSE") == "Poppy'S Playhouse"
    assert wb.value("Lines", "J3") == "Zinc Willie Winkie Candle Stick", "J3: TRIM phải gộp dấu cách đôi ở giữa"


def test_summary(wb, rows):
    for cell, fam in [("B2", ("SUM", "COUNTIF")), ("B3", ("COUNTIF", "SUMPRODUCT")), ("B4", ("COUNTIF", "SUMPRODUCT")),
                      ("B5", ("SUMPRODUCT", "SUM", "COUNTIF"))]:
        need_formula(wb, "Summary", cell, [fam])
    exp = [expected_row(raw) for raw in rows.values()]
    assert wb.value("Summary", "B2") == sum(e["P"] for e in exp) == 83
    assert wb.value("Summary", "B3") == sum(e["L"] == "Cancel" for e in exp) == 5
    assert wb.value("Summary", "B4") == sum(e["M"] == "Guest" for e in exp) == 95
    assert wb.value("Summary", "B5") == sum(str(raw["B"]) != e["I"] for raw, e in zip(rows.values(), exp)) == 17
