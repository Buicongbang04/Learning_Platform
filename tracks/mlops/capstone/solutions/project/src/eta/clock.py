from eta.config import MONTH


def _parse(month: str) -> tuple[int, int]:
    if not MONTH.match(str(month)):
        raise ValueError(f"tháng phải dạng YYYY-MM, nhận {month!r}")
    year, mon = str(month).split("-")
    return int(year), int(mon)


def add_months(month: str, n: int) -> str:
    year, mon = _parse(month)
    index = year * 12 + (mon - 1) + n
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def months_between(start: str, end: str) -> list[str]:
    _parse(end)
    if start > end:
        raise ValueError(f"start {start} sau end {end}")
    months = [start]
    while months[-1] != end:
        months.append(add_months(months[-1], 1))
    return months
