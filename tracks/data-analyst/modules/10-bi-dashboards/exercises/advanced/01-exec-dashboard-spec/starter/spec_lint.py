"""Kiểm spec dashboard (DASHBOARD_SPEC.md) trước khi dựng: đủ phần, bảng KPI đủ cột, không còn TODO.

    uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/advanced/01-exec-dashboard-spec/starter/spec_lint.py
"""
from __future__ import annotations

import sys
from pathlib import Path

SECTIONS = [
    "Người dùng và quyết định",
    "Câu hỏi dashboard trả lời",
    "KPI",
    "Bố cục",
    "Bộ lọc và drill-down",
    "Refresh và cache",
    "Bản dựng",
]
KPI_COLUMNS = ["KPI", "Định nghĩa", "Công thức", "Grain", "So sánh", "Refresh", "Owner"]
MIN_KPI, MAX_KPI = 3, 7


def split_sections(md: str) -> dict[str, str]:
    """{tên heading `## `: nội dung tới heading `## ` kế tiếp}. Heading `#`, `###` không tách phần."""
    sections: dict[str, str] = {}
    current = None
    for line in md.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = ""
        elif current is not None:
            sections[current] += line + "\n"
    return sections


def parse_kpi_table(md: str) -> list[dict[str, str]]:
    """Bảng markdown đầu tiên trong phần `## KPI`: mỗi dòng dữ liệu một dict {tên cột: ô đã strip}.

    Không có phần KPI hoặc không có bảng: []. Bỏ dòng phân cách `| --- |`.
    """
    # TODO
    raise NotImplementedError


def lint_spec(md: str) -> list[str]:
    """Danh sách lỗi (chuỗi tiếng Việt, nêu tên phần / tên KPI / tên cột liên quan). Spec tốt trả [].

    Luật:
    - mỗi phần trong SECTIONS phải có (một lỗi mỗi phần thiếu), có nội dung, không chứa "TODO";
    - bảng KPI có đủ cột KPI_COLUMNS; từ MIN_KPI tới MAX_KPI dòng; tên KPI không trùng (không phân biệt hoa thường
      và khoảng trắng hai đầu); mọi ô của cột bắt buộc khác rỗng (một lỗi mỗi ô rỗng, nêu tên KPI và tên cột).
    """
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("DASHBOARD_SPEC.md")
    problems = lint_spec(path.read_text(encoding="utf-8"))
    print("\n".join(f"- {p}" for p in problems) or "Spec đạt.")
