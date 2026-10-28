"""Table-level lineage từ câu SQL bằng regex."""

from __future__ import annotations

import heapq
import re


def split_statements(script: str) -> list[str]:
    """Tách script theo ';' (đủ dùng cho bài này, không xử lý ';' trong chuỗi)."""
    return [s.strip() for s in script.split(";") if s.strip()]


def normalize(name: str) -> str:
    return name.replace('"', "").lower()


def parse_statement(sql: str) -> tuple[str, set[str]] | None:
    # TODO: làm sạch comment/chuỗi/EXTRACT, tìm target, tìm nguồn, bỏ CTE và chính target
    raise NotImplementedError


def build_graph(statements: list[str]) -> dict[str, set[str]]:
    # TODO
    raise NotImplementedError


def upstream(graph: dict[str, set[str]], table: str) -> set[str]:
    # TODO: mọi tổ tiên
    raise NotImplementedError


def downstream(graph: dict[str, set[str]], table: str) -> set[str]:
    # TODO: mọi hậu duệ
    raise NotImplementedError


def run_order(graph: dict[str, set[str]]) -> list[str]:
    # TODO: Kahn + heapq, ValueError nếu có vòng
    raise NotImplementedError
