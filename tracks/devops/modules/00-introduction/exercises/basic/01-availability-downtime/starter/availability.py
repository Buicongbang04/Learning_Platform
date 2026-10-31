from datetime import datetime, timedelta


def allowed_downtime(slo: float, window: timedelta) -> timedelta:
    # TODO: thời gian được phép sập trong cửa sổ; SLO phải nằm trong (0, 1)
    raise NotImplementedError


def merge_outages(spans: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    # TODO: gộp các khoảng chồng nhau hoặc nối liền nhau, trả danh sách đã sắp
    raise NotImplementedError


def downtime(incidents: list[dict], start: datetime, end: datetime) -> timedelta:
    # TODO: chỉ tính impact "outage", cắt theo cửa sổ [start, end), incident chưa đóng tính tới end
    raise NotImplementedError


def availability(incidents: list[dict], start: datetime, end: datetime) -> float:
    # TODO
    raise NotImplementedError


def budget_remaining(slo: float, incidents: list[dict], start: datetime, end: datetime) -> timedelta:
    # TODO
    raise NotImplementedError
