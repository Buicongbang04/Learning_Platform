def median(values: list[float]) -> float:
    """Trung vị của danh sách số. Danh sách rỗng thì ValueError."""
    if not values:
        raise ValueError("danh sách rỗng")
    ordered = sorted(values)
    return ordered[len(ordered) // 2]
