"""Chỉ mục Zalo Legal dùng lại cache vector bge-m3 của module 13 (không phải phần bài tập, không sửa)."""

import json
from pathlib import Path

import numpy as np

import llmkit


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class LegalIndex:
    """Corpus 61 425 điều + ma trận bge-m3 đã chuẩn hoá L2 (cache tạo ở bài Intermediate 01 module 13)."""

    def __init__(self, root: Path, embed=None):
        root = Path(root)
        docs = _read_jsonl(root / "corpus.jsonl")
        self.uids = [d["_id"] for d in docs]
        self._docs = {d["_id"]: (d["title"], d["text"]) for d in docs}
        cache = root / "cache"
        ids = json.loads((cache / "bge-m3.ids.json").read_text(encoding="utf-8"))
        if ids != self.uids:
            raise ValueError("cache bge-m3 không khớp corpus: chạy lại notebook Intermediate 01 của module 13")
        self.matrix = np.load(cache / "bge-m3.npy")
        self._embed = embed or llmkit.embed

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        q = np.asarray(self._embed([query])[0], dtype=np.float32)
        q /= np.linalg.norm(q) or 1.0
        scores = self.matrix @ q
        top = np.argpartition(-scores, k)[:k]
        top = top[np.lexsort((top, -scores[top]))]
        return [(self.uids[i], float(scores[i])) for i in top]

    def lookup(self, uid: str) -> tuple[str, str]:
        return self._docs[uid]


def load_questions(root: Path, n: int, split: str = "test") -> list[dict]:
    """n query-id đầu tiên của qrels/<split>.jsonl: {"qid", "text", "relevant": set(uid)} (tập ghim của module 13)."""
    root = Path(root)
    relevant: dict[str, set[str]] = {}
    for row in _read_jsonl(root / "qrels" / f"{split}.jsonl"):
        relevant.setdefault(row["query-id"], set()).add(row["corpus-id"])
    texts = {q["_id"]: q["text"] for q in _read_jsonl(root / "queries.jsonl")}
    return [{"qid": qid, "text": texts[qid], "relevant": rel} for qid, rel in list(relevant.items())[:n]]
