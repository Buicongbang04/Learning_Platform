"""DAG, d-separation và backdoor criterion, cộng một hàm OLS để thấy hậu quả bằng số.

Một DAG được biểu diễn bằng danh sách cạnh có hướng: [("Z", "T"), ("Z", "Y"), ("T", "Y")]
nghĩa là Z → T, Z → Y, T → Y. Tên node là chuỗi. Không dùng thư viện đồ thị (networkx...).
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import numpy as np
import pandas as pd

Edges = list[tuple[str, str]]


def _reach(start: set[str], step: dict[str, set[str]]) -> set[str]:
    seen, stack = set(), list(start)
    while stack:
        node = stack.pop()
        for nxt in step.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def descendants(edges: Edges, node: str) -> set[str]:
    """Mọi node đi tới được từ `node` theo chiều mũi tên (không gồm chính `node`)."""
    children = defaultdict(set)
    for a, b in edges:
        children[a].add(b)
    return _reach({node}, children) - {node}


def d_separated(edges: Edges, x: str, y: str, z: set[str]) -> bool:
    """True nếu x và y bị d-separated khi điều kiện trên tập z (moral ancestral graph)."""
    parents = defaultdict(set)
    for a, b in edges:
        parents[b].add(a)
    keep = {x, y, *z}
    keep |= _reach(keep, parents)                       # 1. tập tổ tiên

    neighbours = defaultdict(set)
    for a, b in edges:                                  # 2. bỏ hướng các cạnh trong tập tổ tiên
        if a in keep and b in keep:
            neighbours[a].add(b)
            neighbours[b].add(a)
    for child in keep:                                  #    moralize: nối các cha chung con
        for p, q in combinations(sorted(parents[child] & keep), 2):
            neighbours[p].add(q)
            neighbours[q].add(p)

    blocked = set(z)                                    # 3. xoá z
    open_graph = {n: neighbours[n] - blocked for n in keep - blocked}
    if x in blocked or y in blocked:
        return True
    return y not in _reach({x}, open_graph)             # 4. còn đường nối?


def satisfies_backdoor(edges: Edges, treatment: str, outcome: str, z: set[str]) -> bool:
    """Backdoor criterion: z không chứa hậu duệ của treatment và chặn mọi đường backdoor."""
    if z & descendants(edges, treatment):
        return False
    without_out = [(a, b) for a, b in edges if a != treatment]
    return d_separated(without_out, treatment, outcome, set(z))


def ols_effect(df: pd.DataFrame, treatment: str, outcome: str, adjust: list[str]) -> float:
    """Hệ số của `treatment` khi hồi quy `outcome` ~ 1 + treatment + adjust bằng OLS."""
    X = np.column_stack([np.ones(len(df)), df[[treatment, *adjust]].to_numpy(dtype=float)])
    beta, *_ = np.linalg.lstsq(X, df[outcome].to_numpy(dtype=float), rcond=None)
    return float(beta[1])
