"""Phát hiện data skew và xử lý bằng salting."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F  # noqa: F401


def key_distribution(df: DataFrame, key: str) -> list[tuple]:
    # TODO: groupBy key, count, sắp xếp count giảm dần rồi key tăng dần
    raise NotImplementedError


def partition_sizes(df: DataFrame) -> list[int]:
    # TODO: đếm dòng theo spark_partition_id(), sắp xếp giảm dần
    raise NotImplementedError


def add_salt(df: DataFrame, n_salt: int) -> DataFrame:
    # TODO: thêm cột salt int trong [0, n_salt)
    raise NotImplementedError


def salted_join(big: DataFrame, small: DataFrame, key: str, n_salt: int) -> DataFrame:
    # TODO: salt bên lớn, nhân bản bên nhỏ n_salt lần, join theo (key, salt), bỏ salt
    raise NotImplementedError


def salted_count(df: DataFrame, key: str, n_salt: int) -> DataFrame:
    # TODO: aggregation hai tầng: (key, salt) -> key; cột key, cnt
    raise NotImplementedError
