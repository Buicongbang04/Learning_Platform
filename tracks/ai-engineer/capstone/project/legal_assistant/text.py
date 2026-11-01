"""M01: chuẩn hoá văn bản luật, tokenizer cho BM25, đọc uid điều luật.

Định nghĩa giống module 13 (mục 2 "Unicode NFC" và mục 3 "BM25"): NFC ở cả hai đầu, tách theo âm tiết.
"""

from __future__ import annotations


def normalize(text: str) -> str:
    """NFC; trong mỗi dòng gộp mọi chuỗi khoảng trắng thành một dấu cách và bỏ ở hai đầu; bỏ dòng trống.

    Giữ nguyên ranh giới dòng: chunk theo khoản (M03) dựa vào nó.
    """
    raise NotImplementedError("M01: normalize")


def tokenize(text: str, bigrams: bool = False) -> list[str]:
    """Token âm tiết: NFC, chữ thường, các chuỗi `\\w+`.

    `bigrams=True`: giữ mọi âm tiết rồi nối thêm, theo thứ tự, bigram của từng cặp âm tiết liền kề dạng
    `"giấy_phép"`. Câu hỏi và tài liệu phải đi qua cùng một cấu hình.
    """
    raise NotImplementedError("M01: tokenize")


def split_uid(uid: str) -> tuple[str, int]:
    """`"100/2019/nđ-cp+5"` → `("100/2019/nđ-cp", 5)`: số hiệu văn bản và số điều (phần sau dấu `+` cuối).

    uid không có phần số điều hợp lệ thì `ValueError`.
    """
    raise NotImplementedError("M01: split_uid")
