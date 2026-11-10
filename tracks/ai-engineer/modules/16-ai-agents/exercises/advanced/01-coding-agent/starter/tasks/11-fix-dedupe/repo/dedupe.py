def dedupe(items: list, key=None) -> list:
    """Bỏ trùng, giữ lần xuất hiện đầu tiên theo thứ tự."""
    if key is None:
        return list(set(items))
    seen = {}
    for item in items:
        seen[key(item)] = item
    return list(seen.values())
