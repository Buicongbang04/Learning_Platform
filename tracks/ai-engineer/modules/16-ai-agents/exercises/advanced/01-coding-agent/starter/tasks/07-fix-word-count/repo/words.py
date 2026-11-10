def word_count(text: str) -> dict[str, int]:
    """Số lần xuất hiện của mỗi từ."""
    counts: dict[str, int] = {}
    for word in text.split(" "):
        counts[word] = counts.get(word, 0) + 1
    return counts
