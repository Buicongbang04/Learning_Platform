import base64
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from quillo import oidc

log = logging.getLogger("quillo.auth")

SESSION_COOKIE = "quillo_session"
SESSION_MAX_AGE = 8 * 3600
MAX_ISSUED_DIGITS = 12
USER_SESSION_PREFIX = "u."


def clock() -> float:
    return time.time()


@dataclass(frozen=True)
class User:
    """Người gọi: `admin` (token tĩnh QUILLO_ADMIN_TOKEN, thấy mọi tài liệu) hoặc người dùng OIDC với các nhóm của họ."""

    name: str
    groups: frozenset[str] = frozenset()
    admin: bool = False


ADMIN = User("admin", admin=True)


def token_matches(given: str | None, expected: str) -> bool:
    return given is not None and hmac.compare_digest(given.encode(), expected.encode())


def _sign(token: str, issued: int) -> str:
    return hmac.new(token.encode(), f"v1:{issued}".encode(), hashlib.sha256).hexdigest()


def session_value(token: str, issued: int | None = None) -> str:
    """Cookie phiên `<thời điểm cấp>.<HMAC(token, "v1:<thời điểm cấp>")>`: không chứa token, hết hạn sau SESSION_MAX_AGE."""
    issued = int(clock()) if issued is None else issued
    return f"{issued}.{_sign(token, issued)}"


def session_valid(value: str | None, token: str) -> bool:
    issued, _, signature = (value or "").partition(".")
    if not (issued.isascii() and issued.isdigit() and len(issued) <= MAX_ISSUED_DIGITS):
        return False
    if not token_matches(signature, _sign(token, int(issued))):
        return False
    return 0 <= clock() - int(issued) <= SESSION_MAX_AGE


def sign_payload(key: str, purpose: str, payload: dict) -> str:
    """`<base64url(JSON)>.<HMAC(key, purpose:base64)>`: dữ liệu được ký chứ không mã hoá."""
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    return f"{body}.{hmac.new(key.encode(), f'{purpose}:{body}'.encode(), hashlib.sha256).hexdigest()}"


def read_payload(key: str, purpose: str, value: str | None, max_age: int) -> dict | None:
    body, _, signature = (value or "").partition(".")
    expected = hmac.new(key.encode(), f"{purpose}:{body}".encode(), hashlib.sha256).hexdigest()
    if not body or not token_matches(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except ValueError:
        return None
    issued = payload.get("i") if isinstance(payload, dict) else None
    if not isinstance(issued, int) or not 0 <= clock() - issued <= max_age:
        return None
    return payload


def user_session_value(token: str, user: User) -> str:
    """Cookie phiên của người dùng SSO: tên và nhóm lúc đăng nhập, ký HMAC, hết hạn sau SESSION_MAX_AGE."""
    payload = {"n": user.name, "g": sorted(user.groups), "i": int(clock())}
    return USER_SESSION_PREFIX + sign_payload(token, "u1", payload)


def _bearer(request: Request) -> str | None:
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    return value.strip() if scheme.lower() == "bearer" else None


def session_user(request: Request) -> User | None:
    value = request.cookies.get(SESSION_COOKIE) or ""
    token = request.app.state.settings.admin_token
    if value.startswith(USER_SESSION_PREFIX):
        payload = read_payload(token, "u1", value[len(USER_SESSION_PREFIX):], SESSION_MAX_AGE)
        if payload is None:
            return None
        return User(str(payload.get("n", "")), frozenset(str(g) for g in payload.get("g", [])))
    return ADMIN if session_valid(value, token) else None


def has_session(request: Request) -> bool:
    return session_user(request) is not None


def bearer_user(request: Request) -> User | None:
    token = _bearer(request)
    if token is None:
        return None
    if token_matches(token, request.app.state.settings.admin_token):
        return ADMIN
    provider: oidc.Provider | None = request.app.state.oidc
    if provider is None or token.count(".") != 2:
        return None
    try:
        identity = provider.identity(provider.verify(token))
    except oidc.InvalidToken as error:
        log.info("token OIDC bị từ chối", extra={"fields": {"reason": str(error)}})
        return None
    return User(identity.name, identity.groups)


def current_user(request: Request) -> User | None:
    return bearer_user(request) or session_user(request)


def require_token(request: Request) -> User:
    """Dependency cho /api/*: `Authorization: Bearer <QUILLO_ADMIN_TOKEN hoặc access token OIDC>` hoặc cookie phiên UI."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Cần token", headers={"WWW-Authenticate": "Bearer"})
    return user


require_user = require_token
