"""Kiểm access token (JWT) do IdP của khách cấp trước khi tin các claim trong đó."""

import base64
import binascii
import json
import threading
import time

import jwt
import requests

ALGORITHMS = frozenset({"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"})
LEEWAY = 60
REFETCH_INTERVAL = 5.0
EC_CURVES = {"ES256": "P-256", "ES384": "P-384", "ES512": "P-521"}


class TokenError(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def _fits(raw: dict, alg: str) -> bool:
    """Khoá dùng được cho `alg` của token: theo `alg` của JWK nếu có, không thì theo `kty`/`crv` (Entra ID bỏ `alg`)."""
    if raw.get("alg"):
        return raw["alg"] == alg
    if raw.get("kty") == "RSA":
        return alg[:2] in {"RS", "PS"}
    return raw.get("kty") == "EC" and EC_CURVES.get(alg) == raw.get("crv")


class _Keys:
    """JWKS theo URL. Kid đã biết: chỉ đọc cache, không bao giờ chờ mạng. Kid lạ: tải lại một lần (single-flight, ngoài
    khoá cache), không quá một lần mỗi REFETCH_INTERVAL; trong khoảng đó hoặc khi luồng khác đang tải thì trả None ngay."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.fetching: dict[str, threading.Lock] = {}
        self.cache: dict[str, tuple[dict[str, dict], float]] = {}

    @staticmethod
    def _fetch(url: str) -> dict[str, dict]:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {raw["kid"]: raw for raw in response.json().get("keys", [])
                if isinstance(raw, dict) and raw.get("use", "sig") == "sig" and "kid" in raw
                and raw.get("kty") in {"RSA", "EC"}}

    def get(self, url: str, kid: str) -> dict | None:
        with self.lock:
            keys, attempted = self.cache.get(url, ({}, float("-inf")))
            if kid in keys:
                return keys[kid]
            if time.monotonic() - attempted < REFETCH_INTERVAL:
                return None
            gate = self.fetching.setdefault(url, threading.Lock())
        if not gate.acquire(blocking=not keys):
            return None
        try:
            with self.lock:
                keys, attempted = self.cache.get(url, ({}, float("-inf")))
                if kid in keys or time.monotonic() - attempted < REFETCH_INTERVAL:
                    return keys.get(kid)
                self.cache[url] = (keys, time.monotonic())
            try:
                fresh = self._fetch(url)
            except (requests.RequestException, ValueError):
                return keys.get(kid)
            with self.lock:
                self.cache[url] = (fresh, time.monotonic())
            return fresh.get(kid)
        finally:
            gate.release()


_KEYS = _Keys()


def _segment(part: str) -> dict:
    try:
        value = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    except (binascii.Error, ValueError, UnicodeDecodeError) as error:
        raise TokenError("malformed", "phần header/payload không phải base64url JSON") from error
    if not isinstance(value, dict):
        raise TokenError("malformed", "header/payload không phải object JSON")
    return value


def check(token: str, *, issuer: str, audience: str, jwks_url: str, now: float | None = None) -> dict:
    pieces = token.split(".") if isinstance(token, str) else []
    if len(pieces) != 3 or not all(pieces[:2]):
        raise TokenError("malformed", "JWS compact phải có đúng 3 phần")
    header, _ = _segment(pieces[0]), _segment(pieces[1])
    alg = header.get("alg")
    if alg not in ALGORITHMS:
        raise TokenError("algorithm", f"alg {alg!r} không được chấp nhận")
    key = _KEYS.get(jwks_url, str(header.get("kid", "")))
    if key is None:
        raise TokenError("unknown_key", "kid không có trong JWKS của IdP")
    if not _fits(key, alg):
        raise TokenError("algorithm", "alg của token không hợp với khoá")
    try:
        public = jwt.PyJWK(key, algorithm=alg).key
    except jwt.PyJWTError as error:
        raise TokenError("unknown_key", "khoá trong JWKS không dùng được") from error
    try:
        claims = jwt.decode(token, key=public, algorithms=[alg],
                            options={"verify_exp": False, "verify_nbf": False, "verify_iat": False,
                                     "verify_aud": False, "verify_iss": False})
    except jwt.InvalidSignatureError as error:
        raise TokenError("signature") from error
    except jwt.DecodeError as error:
        raise TokenError("malformed", str(error)) from error
    if claims.get("iss") != issuer:
        raise TokenError("issuer")
    aud = claims.get("aud")
    audiences = [aud] if isinstance(aud, str) else aud if isinstance(aud, list) else []
    if audience not in audiences:
        raise TokenError("audience")
    current = time.time() if now is None else now
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or current > exp + LEEWAY:
        raise TokenError("expired")
    for name in ("nbf", "iat"):
        value = claims.get(name)
        if value is not None and (not isinstance(value, (int, float)) or value > current + LEEWAY):
            raise TokenError("not_yet_valid", name)
    return claims
