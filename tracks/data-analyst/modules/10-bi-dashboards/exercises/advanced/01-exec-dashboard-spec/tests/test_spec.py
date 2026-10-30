import pytest

from testkit import Exercise

ex = Exercise(__file__)

SECTIONS = [
    "Người dùng và quyết định",
    "Câu hỏi dashboard trả lời",
    "KPI",
    "Bố cục",
    "Bộ lọc và drill-down",
    "Refresh và cache",
    "Bản dựng",
]
KPI_HEADER = "| KPI | Định nghĩa | Công thức | Grain | So sánh | Refresh | Owner |\n| --- | --- | --- | --- | --- | --- | --- |\n"


def kpi_row(name, so_sanh="Cùng kỳ năm trước"):
    return f"| {name} | Doanh thu gộp dòng hợp lệ | SUM(revenue) | tuần | {so_sanh} | hằng ngày 6h | Sales Ops |\n"


def spec(kpi_rows=None, drop=None, extra=None):
    rows = kpi_rows if kpi_rows is not None else [kpi_row("Doanh thu"), kpi_row("Số đơn"), kpi_row("AOV")]
    body = {
        "Người dùng và quyết định": "Head of Sales, họp thứ Hai: quyết định dồn ngân sách cho thị trường nào.",
        "Câu hỏi dashboard trả lời": "1. Tuần trước bán thế nào so với cùng kỳ?\n2. Thị trường nào kéo giảm?",
        "KPI": "Ba KPI chính.\n\n" + KPI_HEADER + "".join(rows),
        "Bố cục": "Hàng 1: 3 KPI tile. Hàng 2: trend 12 tuần. Hàng 3: breakdown theo nước.",
        "Bộ lọc và drill-down": "Bộ lọc Quốc gia (mặc định: tất cả). Click nước -> bảng sản phẩm.",
        "Refresh và cache": "Dữ liệu nạp 5h sáng, cache 12 giờ, hiện 'cập nhật lúc' trên đầu.",
        "Bản dựng": "Metabase, script build_dashboard.py, ảnh screenshot.png.",
    }
    if extra:
        body.update(extra)
    parts = ["# Spec dashboard doanh số tuần\n"]
    for name in SECTIONS:
        if name != drop:
            parts.append(f"## {name}\n\n{body[name]}\n")
    return "\n".join(parts)


@pytest.fixture
def lint():
    return ex.module("spec_lint.py")


def test_parse_kpi_table(lint):
    rows = lint.parse_kpi_table(spec())
    assert [r["KPI"] for r in rows] == ["Doanh thu", "Số đơn", "AOV"]
    assert rows[0]["Công thức"] == "SUM(revenue)" and rows[0]["Owner"] == "Sales Ops"
    assert lint.parse_kpi_table(spec(drop="KPI")) == []


def test_spec_tot_khong_co_loi(lint):
    assert lint.lint_spec(spec()) == []


def test_thieu_phan(lint):
    problems = lint.lint_spec(spec(drop="Refresh và cache"))
    assert len(problems) == 1 and "Refresh và cache" in problems[0]


def test_phan_rong_hoac_con_todo(lint):
    problems = lint.lint_spec(spec(extra={"Bố cục": "TODO: vẽ wireframe"}))
    assert len(problems) == 1 and "Bố cục" in problems[0]
    problems = lint.lint_spec(spec(extra={"Bản dựng": ""}))
    assert len(problems) == 1 and "Bản dựng" in problems[0]


def test_luat_bang_kpi(lint):
    assert any("KPI" in p for p in lint.lint_spec(spec(kpi_rows=[kpi_row("Doanh thu"), kpi_row("AOV")]))), (
        "Ít hơn 3 KPI: dashboard điều hành thiếu bức tranh")
    many = [kpi_row(f"KPI {i}") for i in range(8)]
    assert any("KPI" in p for p in lint.lint_spec(spec(kpi_rows=many))), "Hơn 7 KPI: không còn là dashboard tập trung"
    dup = [kpi_row("Doanh thu"), kpi_row("doanh thu "), kpi_row("AOV")]
    assert any("trùng" in p for p in lint.lint_spec(spec(kpi_rows=dup))), "Tên KPI trùng (không phân biệt hoa thường, khoảng trắng)"
    empty = [kpi_row("Doanh thu", so_sanh=" "), kpi_row("Số đơn"), kpi_row("AOV")]
    problems = lint.lint_spec(spec(kpi_rows=empty))
    assert len(problems) == 1 and "Doanh thu" in problems[0] and "So sánh" in problems[0]
    no_col = spec().replace("| Owner |\n", "|\n", 1)
    assert any("Owner" in p for p in lint.lint_spec(no_col)), "Bảng KPI thiếu cột bắt buộc"


def test_spec_cua_ban_dat_lint(lint):
    text = ex.read("DASHBOARD_SPEC.md")
    assert lint.lint_spec(text) == []
    assert "TODO" not in text
