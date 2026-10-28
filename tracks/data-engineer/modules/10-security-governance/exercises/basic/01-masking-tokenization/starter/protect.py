"""Kỹ thuật che PII: masking, pseudonymization, tokenization."""

from __future__ import annotations

import hashlib
import hmac

import pandas as pd
from cryptography.fernet import Fernet


def mask_email(email: str | None) -> str | None:
    """'maria.silva@gmail.com' -> 'm***@gmail.com'."""
    # TODO: xử lý None, chuỗi không có '@', còn lại giữ ký tự đầu + domain
    raise NotImplementedError


def mask_phone(phone: str | None) -> str | None:
    """'+55 (11) 98765-4321' -> '*********4321'."""
    # TODO: lấy chữ số, giữ 4 số cuối
    raise NotImplementedError


def pseudonymize(value: str, key: bytes, length: int = 16) -> str:
    """HMAC-SHA256(key, value), lấy `length` ký tự hex đầu."""
    # TODO
    raise NotImplementedError


class Tokenizer:
    """Tokenization có vault: token -> ciphertext Fernet."""

    def __init__(self, fernet_key: bytes, hmac_key: bytes):
        self.fernet = Fernet(fernet_key)
        self.hmac_key = hmac_key
        self.vault: dict[str, bytes] = {}

    def tokenize(self, value: str) -> str:
        # TODO: token = "tok_" + 24 ký tự hex từ HMAC; lưu ciphertext vào vault
        raise NotImplementedError

    def detokenize(self, token: str) -> str:
        # TODO: KeyError nếu token không có trong vault
        raise NotImplementedError


def mask_dataframe(df: pd.DataFrame, policy: dict[str, str], key: bytes) -> pd.DataFrame:
    """Áp policy {cột: action} với action ∈ email, phone, pseudonym, redact, drop."""
    # TODO: trả DataFrame mới, không sửa df
    raise NotImplementedError
