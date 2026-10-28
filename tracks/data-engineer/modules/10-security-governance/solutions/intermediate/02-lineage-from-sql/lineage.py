"""Table-level lineage từ câu SQL bằng regex (lời giải)."""

from __future__ import annotations

import heapq
import re

NAME = r'[\w."]+'
TARGET_RE = re.compile(
    rf"^\s*(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    rf"|INSERT\s+(?:INTO\s+)?)({NAME})",
    re.I,
)
SOURCE_RE = re.compile(rf"\b(?:FROM|JOIN)\s+({NAME})\b(?!\s*\()", re.I)
CTE_RE = re.compile(r'(?:\bWITH|,)\s*(?:RECURSIVE\s+)?([\w"]+)\s+AS\s*\(', re.I)


def split_statements(script: str) -> list[str]:
    """Tách script theo ';' (đủ dùng cho bài này, không xử lý ';' trong chuỗi)."""
    return [s.strip() for s in script.split(";") if s.strip()]


def normalize(name: str) -> str:
    return name.replace('"', "").lower()


def _clean(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    sql = re.sub(r"\b(?:EXTRACT|TRIM|SUBSTRING)\s*\([^()]*\)", " ", sql, flags=re.I)
    return sql


def parse_statement(sql: str) -> tuple[str, set[str]] | None:
    sql = _clean(sql)
    m = TARGET_RE.match(sql)
    if not m:
        return None
    target = normalize(m.group(1))
    ctes = {normalize(n) for n in CTE_RE.findall(sql)}
    sources = {normalize(n) for n in SOURCE_RE.findall(sql[m.end():])}
    return target, sources - ctes - {target}


def build_graph(statements: list[str]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for stmt in statements:
        parsed = parse_statement(stmt)
        if parsed is None:
            continue
        target, sources = parsed
        graph.setdefault(target, set()).update(sources)
    return graph


def _walk(edges: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        for nxt in edges.get(stack.pop(), set()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    seen.discard(start)
    return seen


def upstream(graph: dict[str, set[str]], table: str) -> set[str]:
    return _walk(graph, table)


def downstream(graph: dict[str, set[str]], table: str) -> set[str]:
    children: dict[str, set[str]] = {}
    for target, sources in graph.items():
        for src in sources:
            children.setdefault(src, set()).add(target)
    return _walk(children, table)


def run_order(graph: dict[str, set[str]]) -> list[str]:
    # chỉ đếm phụ thuộc vào các target khác; bảng raw coi như có sẵn
    pending = {t: {s for s in srcs if s in graph} for t, srcs in graph.items()}
    ready = [t for t, deps in pending.items() if not deps]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        t = heapq.heappop(ready)
        order.append(t)
        for other, deps in pending.items():
            if t in deps:
                deps.remove(t)
                if not deps:
                    heapq.heappush(ready, other)
    if len(order) != len(graph):
        raise ValueError(f"Có vòng lặp giữa: {sorted(set(graph) - set(order))}")
    return order
