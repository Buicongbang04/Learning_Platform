"""Chuẩn hoá văn bản và chunking: cố định theo ký tự, và theo Khoản/Điểm của văn bản luật.

Chỉ dùng thư viện chuẩn trong tệp này (`re`, `unicodedata`).
"""

from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    """Chuẩn hoá NFC; trong mỗi dòng gộp mọi chuỗi khoảng trắng thành một dấu cách và bỏ khoảng
    trắng ở hai đầu dòng; bỏ dòng trống. Các dòng nối lại bằng "\\n"."""
    # TODO
    raise NotImplementedError


def chunk_fixed(text: str, size: int, overlap: int) -> list[str]:
    """Cắt `text` (không chuẩn hoá) theo ký tự: mỗi chunk dài `size`, chunk sau bắt đầu sau chunk
    trước `size - overlap` ký tự; dừng ở chunk đầu tiên chạm cuối văn bản.

    Ném ValueError nếu không có 0 <= overlap < size (size > 0). Văn bản rỗng trả [].
    """
    # TODO
    raise NotImplementedError


def chunk_legal(article_text: str, max_chars: int) -> list[str]:
    """Chunk một Điều luật theo khoản; khoản dài hơn `max_chars` ký tự thì tách tiếp theo điểm.

    Chuẩn hoá bằng `normalize` trước. Dòng đầu là tiêu đề Điều và đứng đầu mọi chunk. Quy tắc đầy đủ
    ở README của bài.
    """
    # TODO
    raise NotImplementedError
