"""Kỹ thuật che PII: masking, pseudonymization, tokenization (lời giải)."""

from __future__ import annotations

import hashlib
import hmac
import re

import pandas as pd
from cryptography.fernet import Fernet


def mask_email(email: str | None) -> str | None:
    """'maria.silva@gmail.com' -> 'm***@gmail.com'."""
    if email is None:
        return None
    local, sep, domain = email.partition("@")
    if not sep or not local:
        return "***"
    return f"{local[0]}***@{domain}"


def mask_phone(phone: str | None) -> str | None:
    """'+55 (11) 98765-4321' -> '*********4321'."""
    if phone is None:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


def pseudonymize(value: str, key: bytes, length: int = 16) -> str:
    """HMAC-SHA256(key, value), lấy `length` ký tự hex đầu."""
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()[:length]


class Tokenizer:
    """Tokenization có vault: token -> ciphertext Fernet."""

    def __init__(self, fernet_key: bytes, hmac_key: bytes):
        self.fernet = Fernet(fernet_key)
        self.hmac_key = hmac_key
        self.vault: dict[str, bytes] = {}

    def tokenize(self, value: str) -> str:
        token = "tok_" + pseudonymize(value, self.hmac_key, length=24)
        if token not in self.vault:
            self.vault[token] = self.fernet.encrypt(value.encode("utf-8"))
        return token

    def detokenize(self, token: str) -> str:
        ciphertext = self.vault[token]  # KeyError nếu không có
        return self.fernet.decrypt(ciphertext).decode("utf-8")


def mask_dataframe(df: pd.DataFrame, policy: dict[str, str], key: bytes) -> pd.DataFrame:
    """Áp policy {cột: action} với action ∈ email, phone, pseudonym, redact, drop."""
    def null_safe(func):
        # pandas có thể biến None thành NaN; giữ giá trị rỗng là None
        return lambda v: None if v is None or pd.isna(v) else func(v)

    actions = {
        "email": null_safe(mask_email),
        "phone": null_safe(mask_phone),
        "pseudonym": null_safe(lambda v: pseudonymize(str(v), key)),
        "redact": lambda v: "REDACTED",
    }
    out = df.copy()
    for col, action in policy.items():
        if action == "drop":
            out = out.drop(columns=[col])
        elif action in actions:
            out[col] = out[col].astype(object).map(actions[action])
        else:
            raise ValueError(f"Action không hỗ trợ: {action}")
    return out
