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
    if goal not in GOALS:
        raise ValueError(f"goal phải là một trong {sorted(GOALS)}, nhận {goal!r}")
    if goal == "trend":
        chart = "small_multiples" if n_categories > 5 else "line"
        return {"chart": chart, "sort": "natural", "zero_baseline": False}
    if goal == "comparison":
        chart = "barh" if n_categories > 7 else "bar"
        return {"chart": chart, "sort": "natural" if ordered else "descending", "zero_baseline": True}
    if goal == "distribution":
        if n_points is not None and n_points < 30:
            return {"chart": "strip", "sort": None, "zero_baseline": False}
        if n_categories > 1:
            return {"chart": "box", "sort": None, "zero_baseline": False}
        return {"chart": "histogram", "sort": None, "zero_baseline": True}
    if goal == "relationship":
        chart = "hexbin" if n_points is not None and n_points > 5000 else "scatter"
        return {"chart": chart, "sort": None, "zero_baseline": False}
    # composition
    if n_categories <= 5:
        return {"chart": "stacked_bar_100", "sort": None, "zero_baseline": True}
    return {"chart": "barh", "sort": "descending", "zero_baseline": True}


def top_n_with_other(values: pd.Series, n: int, other_label: str = "Khác") -> pd.Series:
    """Giữ n nhóm có giá trị lớn nhất (giảm dần), cộng phần còn lại vào một dòng other_label ở cuối.

    Không thêm dòng other_label nếu không còn nhóm nào. Giữ tên Series.
    """
    ordered = values.sort_values(ascending=False, kind="stable")
    top = ordered.iloc[:n]
    rest = ordered.iloc[n:]
    if len(rest) == 0:
        return top
    other = pd.Series([rest.sum()], index=[other_label], name=values.name)
    return pd.concat([top, other])


def category_share(df: pd.DataFrame, col: str, n: int, other_label: str = "Khác",
                   missing_label: str = "(thiếu)") -> pd.DataFrame:
    """Bảng dữ liệu cho bar chart "tỉ trọng theo nhóm" của cột col.

    NaN được đếm thành nhóm missing_label (không bị bỏ im lặng). Giữ top n nhóm theo số dòng, gộp
    phần còn lại vào other_label ở cuối. Kết quả: index là tên nhóm, cột count (int) và share
    (count / tổng số dòng, cộng lại bằng 1).
    """
    counts = df[col].fillna(missing_label).value_counts()
    counts = top_n_with_other(counts, n, other_label)
    return pd.DataFrame({"count": counts.astype(int), "share": counts / counts.sum()})
