"""Tokenizer âm tiết tiếng Việt và BM25 kiểu Lucene, viết bằng numpy.

Chỉ dùng thư viện chuẩn và numpy trong tệp này.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

import numpy as np

WORD = re.compile(r"\w+")


def tokenize_vi(text: str) -> list[str]:
    """NFC, chữ thường, bỏ dấu câu, tách theo khoảng trắng: mỗi token là một âm tiết (hoặc một số)."""
    return WORD.findall(unicodedata.normalize("NFC", text).lower())


class BM25:
    """BM25 với IDF dạng Lucene: ln(1 + (N - n + 0.5) / (n + 0.5))."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.n_docs = len(docs)
        lengths = np.array([len(d) for d in docs], dtype=float)
        avgdl = lengths.mean() if self.n_docs else 0.0
        # mẫu số chỉ phụ thuộc tài liệu (không phụ thuộc term): tính một lần lúc index
        self._norm = k1 * (1 - b + b * lengths / avgdl) if avgdl > 0 else np.full(self.n_docs, k1 * (1 - b))
        # inverted index: term -> (chỉ số tài liệu, tần suất trong tài liệu đó)
        postings: dict[str, tuple[list[int], list[int]]] = {}
        for i, doc in enumerate(docs):
            for term, freq in Counter(doc).items():
                ids, tfs = postings.setdefault(term, ([], []))
                ids.append(i)
                tfs.append(freq)
        self._postings = {t: (np.array(ids), np.array(tfs, dtype=float)) for t, (ids, tfs) in postings.items()}
        self.idf = {
            t: math.log(1 + (self.n_docs - len(ids) + 0.5) / (len(ids) + 0.5)) for t, (ids, _) in self._postings.items()
        }

    def scores(self, query: list[str]) -> np.ndarray:
        """Điểm BM25 của câu hỏi (đã tokenize) với từng tài liệu, shape (N,). Term lặp lại được cộng mỗi lần."""
        out = np.zeros(self.n_docs)
        for term in query:
            if term not in self._postings:
                continue
            ids, tf = self._postings[term]
            out[ids] += self.idf[term] * tf * (self.k1 + 1) / (tf + self._norm[ids])
        return out

    def top_k(self, query: list[str], k: int) -> list[int]:
        """Chỉ số k tài liệu điểm cao nhất, giảm dần; bằng điểm thì chỉ số nhỏ đứng trước."""
        order = np.argsort(-self.scores(query), kind="stable")
        return [int(i) for i in order[:k]]
