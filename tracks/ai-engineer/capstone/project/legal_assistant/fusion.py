"""M02: dense retrieval và hybrid (module 12, module 13 mục 3).

Điểm dense là tích vô hướng với vector đã chuẩn hoá L2 (= cosine).
"""

from __future__ import annotations

import numpy as np


def normalize_rows(matrix: np.ndarray) -> tuple[np.ndarray, int]:
    """Chuẩn hoá L2 từng dòng (float32, không sửa đầu vào). Trả (ma trận mới, số dòng hỏng).

    Dòng có NaN/inf thành toàn 0; dòng toàn 0 giữ nguyên 0. "Dòng hỏng" là dòng thuộc một trong hai loại đó.
    """
    raise NotImplementedError("M02: normalize_rows")


def dense_top_k(matrix: np.ndarray, query: np.ndarray, k: int) -> list[int]:
    """Chỉ số k dòng có tích vô hướng với `query` lớn nhất, giảm dần; bằng điểm thì chỉ số nhỏ trước."""
    raise NotImplementedError("M02: dense_top_k")


def max_by_article(article_ids: list[str], scores: list[float]) -> list[tuple[str, float]]:
    """Gộp điểm mức chunk lên mức điều: điểm của một điều là điểm cao nhất trong các chunk của nó.

    Trả `[(uid, điểm)]` giảm dần theo điểm, bằng điểm thì uid nhỏ trước. Hai danh sách khác độ dài: `ValueError`.
    """
    raise NotImplementedError("M02: max_by_article")


def rrf(rankings: list[list[str]], k: int = 60, weights: list[float] | None = None) -> list[str]:
    """Reciprocal Rank Fusion: điểm(d) = Σ_r w_r / (k + hạng_r(d)), hạng từ 1, tài liệu vắng mặt không được cộng.

    `weights=None` nghĩa là mọi danh sách trọng số 1. Trả mọi id giảm dần theo điểm, bằng điểm thì id nhỏ trước.
    Số trọng số khác số danh sách: `ValueError`.
    """
    raise NotImplementedError("M02: rrf")
