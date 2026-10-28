"""MapReduce bằng tay và bằng RDD."""

from collections import defaultdict  # noqa: F401


def map_phase(lines: list[str]) -> list[tuple[str, int]]:
    # TODO: "o1, Health_Beauty " -> ("health_beauty", 1); bỏ category rỗng
    raise NotImplementedError


def shuffle_phase(pairs: list[tuple[str, int]]) -> dict[str, list[int]]:
    # TODO: gom value theo key, key sắp xếp tăng dần
    raise NotImplementedError


def reduce_phase(groups: dict[str, list[int]]) -> dict[str, int]:
    # TODO: cộng các value của từng key
    raise NotImplementedError


def rdd_category_count(sc, lines: list[str]) -> list[tuple[str, int]]:
    # TODO: parallelize -> map -> filter -> reduceByKey -> sortByKey -> collect
    raise NotImplementedError


def top_categories(sc, lines: list[str], n: int) -> list[tuple[str, int]]:
    # TODO: reduceByKey rồi takeOrdered theo (-count, category)
    raise NotImplementedError
