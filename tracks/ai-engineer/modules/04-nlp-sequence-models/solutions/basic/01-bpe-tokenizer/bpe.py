"""Byte-level BPE tokenizer tự viết, có chuẩn hoá Unicode cho tiếng Việt.

Quy ước (giống GPT-2 / tiktoken):
- Token cơ sở là 256 byte (id 0..255). Merge thứ i tạo token mới id 256 + i.
- Văn bản được chuẩn hoá NFC, rồi tách thành "pretoken" bằng PRETOKEN_RE; merge không bao giờ
  vượt qua ranh giới pretoken (một token không chứa nửa từ này nửa từ kia).
"""

import re
import unicodedata
from collections import Counter

# Từ (chữ cái/số, kể cả chữ có dấu tiếng Việt) kèm tối đa một dấu cách đứng trước; cụm dấu câu kèm
# dấu cách đứng trước; cụm khoảng trắng. Ghép các pretoken lại đúng bằng văn bản gốc.
PRETOKEN_RE = re.compile(r" ?[^\W_]+| ?[^\s\w]+| ?_+|\s+(?!\S)|\s+")


def normalize(text: str) -> str:
    """Chuẩn hoá Unicode về dạng NFC (dấu tổ hợp gộp vào chữ cái)."""
    return unicodedata.normalize("NFC", text)


def pretokenize(text: str) -> list[str]:
    """Chuẩn hoá NFC rồi tách thành pretoken theo PRETOKEN_RE. "".join(kết quả) == normalize(text)."""
    return PRETOKEN_RE.findall(normalize(text))


def _merge(ids: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
    out, i = [], 0
    while i < len(ids):
        if i + 1 < len(ids) and ids[i] == pair[0] and ids[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out


def train_bpe(texts: list[str], vocab_size: int) -> list[tuple[int, int]]:
    """Học danh sách merge (theo thứ tự) để từ điển có tối đa `vocab_size` token (kể cả 256 byte).

    Mỗi vòng: đếm mọi cặp token liền nhau trong từng pretoken (nhân với tần suất pretoken), chọn cặp
    nhiều nhất; hoà thì chọn cặp có (id trái, id phải) nhỏ nhất. Dừng sớm khi cặp tốt nhất xuất hiện < 2 lần.
    """
    word_freq = Counter(chunk for text in texts for chunk in pretokenize(text))
    words = [(list(w.encode("utf-8")), f) for w, f in word_freq.items()]
    merges: list[tuple[int, int]] = []
    for new_id in range(256, vocab_size):
        counts: Counter = Counter()
        for ids, f in words:
            for pair in zip(ids, ids[1:]):
                counts[pair] += f
        if not counts:
            break
        best = max(counts, key=lambda p: (counts[p], -p[0], -p[1]))
        if counts[best] < 2:
            break
        merges.append(best)
        words = [(_merge(ids, best, new_id), f) for ids, f in words]
    return merges


def encode(text: str, merges: list[tuple[int, int]]) -> list[int]:
    """Văn bản → danh sách id. Trong mỗi pretoken, lặp lại: ghép cặp có thứ hạng merge thấp nhất."""
    ranks = {pair: 256 + i for i, pair in enumerate(merges)}
    out: list[int] = []
    cache: dict[str, list[int]] = {}
    for chunk in pretokenize(text):
        if chunk not in cache:
            ids = list(chunk.encode("utf-8"))
            while len(ids) >= 2:
                pair = min(zip(ids, ids[1:]), key=lambda p: ranks.get(p, float("inf")))
                if pair not in ranks:
                    break
                ids = _merge(ids, pair, ranks[pair])
            cache[chunk] = ids
        out.extend(cache[chunk])
    return out


def decode(ids: list[int], merges: list[tuple[int, int]]) -> str:
    """Danh sách id → văn bản. Byte UTF-8 không hợp lệ thay bằng U+FFFD."""
    vocab = {i: bytes([i]) for i in range(256)}
    for i, (a, b) in enumerate(merges):
        vocab[256 + i] = vocab[a] + vocab[b]
    return b"".join(vocab[i] for i in ids).decode("utf-8", errors="replace")
