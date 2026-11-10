"""M01: đọc Zalo Legal dạng BEIR (corpus.jsonl, queries.jsonl, qrels/<split>.jsonl).

Tập đánh giá ghim của cả track: `load_questions(root, "test", 300)`, tức 300 `query-id` đầu tiên theo thứ tự
xuất hiện trong `qrels/test.jsonl` (module 13). Split train để dành cho fine-tune (M05) và tune tham số.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Article:
    uid: str
    title: str
    text: str


@dataclass(frozen=True)
class Question:
    qid: str
    text: str
    relevant: frozenset[str]


def load_corpus(root: Path) -> list[Article]:
    """Mọi điều luật trong `root/corpus.jsonl`, giữ thứ tự tệp (`_id`, `title`, `text`)."""
    raise NotImplementedError("M01: load_corpus")


def load_questions(root: Path, split: str = "test", n: int | None = None) -> list[Question]:
    """Câu hỏi có nhãn của `qrels/<split>.jsonl`.

    Thứ tự là thứ tự **xuất hiện đầu tiên** của `query-id` trong tệp qrels; `n` lấy `n` câu đầu theo thứ tự đó.
    `relevant` gom mọi `corpus-id` có `score > 0` của câu đó, kể cả khi các dòng không liền nhau.
    """
    raise NotImplementedError("M01: load_questions")
