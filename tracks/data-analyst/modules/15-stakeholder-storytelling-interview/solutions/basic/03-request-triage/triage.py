"""Phân loại và xếp ưu tiên hàng đợi yêu cầu phân tích (xem README của bài)."""

import math

import pandas as pd

HALF_DAY_HOURS = 4      # > nửa ngày là dự án
HIGH_IMPACT = 4         # impact >= 4 là cao
LOW_EFFORT_HOURS = 8    # effort <= 8 giờ là thấp
WORK_ROUTES = {"dashboard", "project", "ad-hoc"}  # những loại tốn giờ làm, cần xếp lịch
QUADRANT_ORDER = ["quick win", "big bet", "fill-in", "money pit"]


def _missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def classify(request: dict) -> str:
    """Trả "self-serve", "clarify", "dashboard", "project" hoặc "ad-hoc" theo đúng thứ tự quy tắc trong README."""
    if bool(request["in_dashboard"]):
        return "self-serve"
    if _missing(request["decision"]):
        return "clarify"
    if bool(request["recurring"]):
        return "dashboard"
    if request["effort_hours"] > HALF_DAY_HOURS:
        return "project"
    return "ad-hoc"


def quadrant(impact: float, effort_hours: float) -> str:
    """Góc phần tư impact/effort: "quick win", "big bet", "fill-in" hoặc "money pit"."""
    high = impact >= HIGH_IMPACT
    low_effort = effort_hours <= LOW_EFFORT_HOURS
    if high:
        return "quick win" if low_effort else "big bet"
    return "fill-in" if low_effort else "money pit"


def prioritize(requests: pd.DataFrame) -> pd.DataFrame:
    """Bản sao có thêm cột route, quadrant, score (= impact / effort_hours), sắp theo thứ tự xử lý."""
    out = requests.copy()
    out["route"] = [classify(row) for row in out.to_dict("records")]
    out["quadrant"] = [quadrant(i, e) for i, e in zip(out["impact"], out["effort_hours"])]
    out["score"] = out["impact"] / out["effort_hours"]

    work = out[out["route"].isin(WORK_ROUTES)].copy()
    work["_q"] = work["quadrant"].map(QUADRANT_ORDER.index)
    work = work.sort_values(["_q", "score", "id"], ascending=[True, False, True]).drop(columns="_q")
    rest = out[~out["route"].isin(WORK_ROUTES)].sort_values("id")
    return pd.concat([work, rest]).reset_index(drop=True)


def plan_week(requests: pd.DataFrame, capacity_hours: float) -> list[str]:
    """Danh sách id được xếp vào tuần: duyệt theo prioritize, chỉ WORK_ROUTES, bỏ "money pit", lấy nếu còn vừa giờ."""
    left = capacity_hours
    chosen = []
    for row in prioritize(requests).itertuples(index=False):
        if row.route not in WORK_ROUTES or row.quadrant == "money pit":
            continue
        if row.effort_hours <= left:
            chosen.append(row.id)
            left -= row.effort_hours
    return chosen


if __name__ == "__main__":
    from pathlib import Path

    backlog = pd.read_csv(Path(__file__).with_name("backlog.csv"))
    print(prioritize(backlog)[["id", "requester", "route", "quadrant", "score", "effort_hours"]].to_string(index=False))
    print("Lịch tuần 30 giờ:", plan_week(backlog, 30))
