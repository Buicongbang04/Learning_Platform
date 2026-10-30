"""Phân loại và xếp ưu tiên hàng đợi yêu cầu phân tích (xem README của bài)."""

import math

import pandas as pd

HALF_DAY_HOURS = 4      # > nửa ngày là dự án
HIGH_IMPACT = 4         # impact >= 4 là cao
LOW_EFFORT_HOURS = 8    # effort <= 8 giờ là thấp
WORK_ROUTES = {"dashboard", "project", "ad-hoc"}  # những loại tốn giờ làm, cần xếp lịch
QUADRANT_ORDER = ["quick win", "big bet", "fill-in", "money pit"]


def classify(request: dict) -> str:
    """Trả "self-serve", "clarify", "dashboard", "project" hoặc "ad-hoc" theo đúng thứ tự quy tắc trong README."""
    # TODO: 1. in_dashboard -> "self-serve"
    # TODO: 2. decision thiếu (None, NaN, chuỗi rỗng hoặc chỉ khoảng trắng) -> "clarify"
    # TODO: 3. recurring -> "dashboard"; 4. effort_hours > HALF_DAY_HOURS -> "project"; 5. còn lại "ad-hoc"
    raise NotImplementedError


def quadrant(impact: float, effort_hours: float) -> str:
    """Góc phần tư impact/effort: "quick win", "big bet", "fill-in" hoặc "money pit"."""
    # TODO
    raise NotImplementedError


def prioritize(requests: pd.DataFrame) -> pd.DataFrame:
    """Bản sao có thêm cột route, quadrant, score (= impact / effort_hours), sắp theo thứ tự xử lý."""
    # TODO: thêm 3 cột cho mọi dòng
    # TODO: dòng có route thuộc WORK_ROUTES lên trước, sắp theo QUADRANT_ORDER, rồi score giảm dần, rồi id tăng dần
    # TODO: các dòng còn lại (self-serve, clarify) ở cuối, sắp theo id; index 0..n-1
    raise NotImplementedError


def plan_week(requests: pd.DataFrame, capacity_hours: float) -> list[str]:
    """Danh sách id được xếp vào tuần: duyệt theo prioritize, chỉ WORK_ROUTES, bỏ "money pit", lấy nếu còn vừa giờ."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    from pathlib import Path

    backlog = pd.read_csv(Path(__file__).with_name("backlog.csv"))
    print(prioritize(backlog)[["id", "requester", "route", "quadrant", "score", "effort_hours"]].to_string(index=False))
    print("Lịch tuần 30 giờ:", plan_week(backlog, 30))
