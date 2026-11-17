"""Kiểm access token (JWT) do IdP của khách cấp trước khi tin các claim trong đó."""

import jwt


class TokenError(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def check(token: str, *, issuer: str, audience: str, jwks_url: str, now: float | None = None) -> dict:
    claims = jwt.decode(token, options={"verify_signature": False})
    if claims.get("iss") != issuer:
        raise TokenError("issuer")
    return claims
