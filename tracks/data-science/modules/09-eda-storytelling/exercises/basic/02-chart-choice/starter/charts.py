"""Chọn biểu đồ theo câu hỏi và chuẩn bị dữ liệu cho bar chart."""

from __future__ import annotations

import pandas as pd

GOALS = {"trend", "comparison", "distribution", "relationship", "composition"}


def choose_chart(goal: str, *, n_categories: int = 1, n_points: int | None = None,
                 ordered: bool = False) -> dict:
    """Chart spec theo bảng quy tắc trong README của bài.

    goal          "trend" | "comparison" | "distribution" | "relationship" | "composition"
    n_categories  số chuỗi (trend), số nhóm (comparison, distribution) hoặc số phần (composition)
    n_points      số quan sát (distribution, relationship); None nếu không biết
    ordered       nhóm có thứ tự tự nhiên (tháng, bucket, số sao)

    Trả {"chart": str, "sort": "descending" | "natural" | None, "zero_baseline": bool}.
    goal không hợp lệ → ValueError.
    """
    # TODO: cài đúng bảng quy tắc trong README
    raise NotImplementedError


def top_n_with_other(values: pd.Series, n: int, other_label: str = "Khác") -> pd.Series:
    """Giữ n nhóm có giá trị lớn nhất (giảm dần), cộng phần còn lại vào một dòng other_label ở cuối.

    Không thêm dòng other_label nếu không còn nhóm nào. Giữ tên Series.
    """
    # TODO
    raise NotImplementedError


def category_share(df: pd.DataFrame, col: str, n: int, other_label: str = "Khác",
                   missing_label: str = "(thiếu)") -> pd.DataFrame:
    """Bảng dữ liệu cho bar chart "tỉ trọng theo nhóm" của cột col.

    NaN được đếm thành nhóm missing_label (không bị bỏ im lặng). Giữ top n nhóm theo số dòng, gộp
    phần còn lại vào other_label ở cuối. Kết quả: index là tên nhóm, cột count (int) và share
    (count / tổng số dòng, cộng lại bằng 1).
    """
    # TODO: dùng top_n_with_other
    raise NotImplementedError
