"""DAG, d-separation và backdoor criterion, cộng một hàm OLS để thấy hậu quả bằng số.

Một DAG được biểu diễn bằng danh sách cạnh có hướng: [("Z", "T"), ("Z", "Y"), ("T", "Y")]
nghĩa là Z → T, Z → Y, T → Y. Tên node là chuỗi. Không dùng thư viện đồ thị (networkx...).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

Edges = list[tuple[str, str]]


def descendants(edges: Edges, node: str) -> set[str]:
    """Mọi node đi tới được từ `node` theo chiều mũi tên (không gồm chính `node`)."""
    # TODO: duyệt BFS/DFS theo danh sách con
    raise NotImplementedError


def d_separated(edges: Edges, x: str, y: str, z: set[str]) -> bool:
    """True nếu x và y bị d-separated khi điều kiện trên tập z.

    Thuật toán gợi ý (moral ancestral graph, Lauritzen 1990):
      1. Giữ lại x, y, z và mọi tổ tiên của chúng (cùng các cạnh giữa các node đó).
      2. "Moralize": với mỗi node, nối mọi cặp cha của nó; rồi bỏ hướng mọi cạnh.
      3. Xoá các node trong z.
      4. x và y d-separated khi và chỉ khi không còn đường nối giữa chúng.
    """
    # TODO
    raise NotImplementedError


def satisfies_backdoor(edges: Edges, treatment: str, outcome: str, z: set[str]) -> bool:
    """Backdoor criterion (Pearl): z hợp lệ để điều chỉnh khi
      (i) không node nào trong z là hậu duệ của treatment, và
      (ii) z chặn mọi đường backdoor: trong đồ thị đã bỏ mọi cạnh đi RA từ treatment,
           treatment và outcome d-separated khi điều kiện trên z.
    """
    # TODO: dùng descendants và d_separated
    raise NotImplementedError


def ols_effect(df: pd.DataFrame, treatment: str, outcome: str, adjust: list[str]) -> float:
    """Hệ số của `treatment` khi hồi quy `outcome` ~ 1 + treatment + adjust bằng OLS.

    Dùng numpy (np.linalg.lstsq), không dùng statsmodels.
    """
    # TODO: ma trận X = [1, treatment, adjust...]; trả hệ số thứ hai
    raise NotImplementedError
