"""Client embedding kiểu OpenAI (`POST /v1/embeddings`): dựng request, đọc response, chia lô, cache.

Chỉ dùng thư viện chuẩn và numpy. Không gọi mạng trong tệp này: hàm gửi request được truyền vào (`embed_fn`).
"""

from __future__ import annotations

import base64
import hashlib
from typing import Callable

import numpy as np

ENCODINGS = ("float", "base64")


def build_request(texts: list[str], model: str, *, dimensions: int | None = None,
                  encoding_format: str = "float") -> dict:
    """Body JSON cho POST /v1/embeddings. Chỉ có khoá `dimensions` khi được truyền.

    ValueError nếu `texts` rỗng, có chuỗi rỗng hoặc chỉ khoảng trắng, hoặc `encoding_format` không hợp lệ.
    """
    texts = list(texts)
    if not texts:
        raise ValueError("texts rỗng")
    if any(not t.strip() for t in texts):
        raise ValueError("có văn bản rỗng: API từ chối cả request")
    if encoding_format not in ENCODINGS:
        raise ValueError(f"encoding_format phải là một trong {ENCODINGS}")
    body = {"model": model, "input": texts, "encoding_format": encoding_format}
    if dimensions is not None:
        body["dimensions"] = int(dimensions)
    return body


def parse_response(payload: dict, n_expected: int | None = None) -> np.ndarray:
    """Ma trận float32 (n, d) theo đúng thứ tự input (trường `index` của từng phần tử trong `data`).

    `embedding` là list số, hoặc chuỗi base64 của các float32 little-endian. ValueError nếu số dòng khác
    `n_expected` (khi truyền), `index` không phải đúng 0..n-1, hoặc các vector khác số chiều.
    """
    rows = {}
    for item in payload["data"]:
        emb = item["embedding"]
        if isinstance(emb, str):
            vec = np.frombuffer(base64.b64decode(emb), dtype="<f4")
        else:
            vec = np.asarray(emb, dtype=np.float32)
        rows[int(item["index"])] = vec
    n = len(payload["data"])
    if sorted(rows) != list(range(n)):
        raise ValueError("index trong response không phải 0..n-1")
    if n_expected is not None and n != n_expected:
        raise ValueError(f"response có {n} vector, cần {n_expected}")
    if len({v.shape for v in rows.values()}) > 1:
        raise ValueError("các vector khác số chiều")
    return np.stack([rows[i] for i in range(n)]).astype(np.float32)


def batched(texts: list[str], max_items: int, max_chars: int) -> list[list[int]]:
    """Chia chỉ số 0..n-1 thành các lô liên tiếp, tham lam: thêm văn bản tiếp theo vào lô hiện tại nếu lô vẫn
    có tối đa `max_items` văn bản và tổng số ký tự tối đa `max_chars`; nếu không thì mở lô mới. Văn bản dài hơn
    `max_chars` đứng một mình một lô."""
    batches: list[list[int]] = []
    current: list[int] = []
    chars = 0
    for i, text in enumerate(texts):
        if current and (len(current) + 1 > max_items or chars + len(text) > max_chars):
            batches.append(current)
            current, chars = [], 0
        current.append(i)
        chars += len(text)
    if current:
        batches.append(current)
    return batches


def cache_key(model: str, text: str) -> str:
    """sha256 hex của model + byte 0 + text (UTF-8): cùng văn bản qua hai model khác nhau là hai khoá khác nhau."""
    return hashlib.sha256(model.encode("utf-8") + b"\x00" + text.encode("utf-8")).hexdigest()


def embed_cached(texts: list[str], model: str, embed_fn: Callable[[list[str]], np.ndarray], cache: dict,
                 *, max_items: int = 32, max_chars: int = 8000) -> np.ndarray:
    """Embed `texts` (float32, đúng thứ tự), chỉ gửi văn bản chưa có trong `cache` (dict cache_key -> vector).

    Văn bản lặp lại trong cùng lời gọi chỉ gửi một lần. Văn bản cần gửi được chia lô bằng `batched` theo thứ tự
    xuất hiện đầu tiên; mỗi lô là một lời gọi `embed_fn(list_văn_bản)`. Vector mới được ghi vào `cache`.
    """
    missing: list[str] = []
    seen: set[str] = set()
    for text in texts:
        key = cache_key(model, text)
        if key not in cache and key not in seen:
            seen.add(key)
            missing.append(text)
    for batch in batched(missing, max_items, max_chars):
        chunk = [missing[i] for i in batch]
        vectors = np.asarray(embed_fn(chunk), dtype=np.float32)
        for text, vec in zip(chunk, vectors):
            cache[cache_key(model, text)] = vec
    return np.stack([cache[cache_key(model, t)] for t in texts]).astype(np.float32)


def truncate(vectors: np.ndarray, dim: int) -> np.ndarray:
    """Giữ `dim` chiều đầu của mỗi vector rồi chuẩn hoá L2 lại (vector 0 giữ 0). float32."""
    v = np.asarray(vectors, dtype=np.float32)[..., :dim]
    norms = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(norms == 0, 1, norms)
