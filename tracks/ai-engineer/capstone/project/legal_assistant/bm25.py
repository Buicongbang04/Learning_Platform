"""M01: BM25 kiểu Lucene (IDF ln(1 + (N - n + 0.5) / (n + 0.5))), như bài Basic 02 module 13.

Bạn có thể chép lời giải của mình ở module 13 vào đây. Chỉ cần numpy và thư viện chuẩn.
"""

from __future__ import annotations

import numpy as np


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        """`docs`: tài liệu đã tokenize. Dựng inverted index một lần ở đây."""
        raise NotImplementedError("M01: BM25.__init__")

    def scores(self, query: list[str]) -> np.ndarray:
        """Điểm BM25 của câu hỏi (đã tokenize) với từng tài liệu, shape (N,). Term lặp lại được cộng mỗi lần."""
        raise NotImplementedError("M01: BM25.scores")

    def top_k(self, query: list[str], k: int) -> list[int]:
        """Chỉ số k tài liệu điểm cao nhất, giảm dần; bằng điểm thì chỉ số nhỏ đứng trước."""
        raise NotImplementedError("M01: BM25.top_k")
