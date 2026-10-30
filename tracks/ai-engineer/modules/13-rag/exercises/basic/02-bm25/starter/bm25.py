"""Tokenizer âm tiết tiếng Việt và BM25 kiểu Lucene, viết bằng numpy.

Chỉ dùng thư viện chuẩn và numpy trong tệp này.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

import numpy as np


def tokenize_vi(text: str) -> list[str]:
    """NFC, chữ thường, bỏ dấu câu, tách theo khoảng trắng: mỗi token là một âm tiết (hoặc một số)."""
    # TODO
    raise NotImplementedError


class BM25:
    """BM25 với IDF dạng Lucene: ln(1 + (N - n + 0.5) / (n + 0.5)).

    `docs` là danh sách tài liệu đã tokenize. Dựng mọi thống kê cần cho chấm điểm ở đây, một lần.
    """

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        # TODO
        raise NotImplementedError

    def scores(self, query: list[str]) -> np.ndarray:
        """Điểm BM25 của câu hỏi (đã tokenize) với từng tài liệu, np.ndarray float shape (N,).

        Term lặp lại trong câu hỏi được cộng mỗi lần nó xuất hiện.
        """
        # TODO
        raise NotImplementedError

    def top_k(self, query: list[str], k: int) -> list[int]:
        """Chỉ số (int) của min(k, N) tài liệu điểm cao nhất, giảm dần; bằng điểm thì chỉ số nhỏ đứng trước."""
        # TODO
        raise NotImplementedError
