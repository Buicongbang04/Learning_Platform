def paginate(items: list, page: int, size: int) -> list:
    """Phần tử của trang `page` (đánh số từ 1), mỗi trang `size` phần tử."""
    start = page * size
    return items[start:start + size]
