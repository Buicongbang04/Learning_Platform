"""MapReduce bằng tay và bằng RDD (lời giải)."""

from collections import defaultdict


def _parse(line: str) -> str:
    parts = line.split(",", 1)
    return parts[1].strip().lower() if len(parts) == 2 else ""


def map_phase(lines: list[str]) -> list[tuple[str, int]]:
    return [(cat, 1) for cat in map(_parse, lines) if cat]


def shuffle_phase(pairs: list[tuple[str, int]]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for key, value in pairs:
        groups[key].append(value)
    return {key: groups[key] for key in sorted(groups)}


def reduce_phase(groups: dict[str, list[int]]) -> dict[str, int]:
    return {key: sum(values) for key, values in groups.items()}


def _counts(sc, lines):
    # Hàm gửi sang executor phải định nghĩa bên trong (closure) để cloudpickle tuần tự hoá theo giá trị.
    # Hàm ở mức module bị pickle theo tên module, mà worker không import được module do testkit nạp.
    def parse(line):
        parts = line.split(",", 1)
        return parts[1].strip().lower() if len(parts) == 2 else ""

    return (
        sc.parallelize(lines, 3)
        .map(parse)
        .filter(lambda cat: cat != "")
        .map(lambda cat: (cat, 1))
        .reduceByKey(lambda a, b: a + b)
    )


def rdd_category_count(sc, lines: list[str]) -> list[tuple[str, int]]:
    return _counts(sc, lines).sortByKey().collect()


def top_categories(sc, lines: list[str], n: int) -> list[tuple[str, int]]:
    return _counts(sc, lines).takeOrdered(n, key=lambda kv: (-kv[1], kv[0]))
