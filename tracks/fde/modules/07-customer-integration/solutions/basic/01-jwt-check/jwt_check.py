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
MIN_REFETCH = 1.0


class TokenError(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


class _Keys:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.cache: dict[str, tuple[dict[str, jwt.PyJWK], float]] = {}

    def _fetch(self, url: str) -> dict[str, jwt.PyJWK]:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        keys = {}
        for raw in response.json().get("keys", []):
            if raw.get("use", "sig") != "sig" or "kid" not in raw or raw.get("alg") not in ALGORITHMS:
                continue
            try:
                keys[raw["kid"]] = jwt.PyJWK(raw)
            except jwt.PyJWTError:
                continue
        return keys

    def get(self, url: str, kid: str) -> jwt.PyJWK | None:
        with self.lock:
            keys, fetched = self.cache.get(url, ({}, 0.0))
            if kid not in keys:
                time.sleep(max(0.0, fetched + MIN_REFETCH - time.monotonic()))
                keys, fetched = self._fetch(url), time.monotonic()
                self.cache[url] = (keys, fetched)
            return keys.get(kid)


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
    if key.algorithm_name != alg:
        raise TokenError("algorithm", "alg của token khác alg của khoá")
    try:
        claims = jwt.decode(token, key=key.key, algorithms=[alg],
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
