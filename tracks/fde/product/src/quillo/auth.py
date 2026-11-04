import hashlib
import hmac
import time

from fastapi import HTTPException, Request

SESSION_COOKIE = "quillo_session"
SESSION_MAX_AGE = 8 * 3600
MAX_ISSUED_DIGITS = 12


def clock() -> float:
    return time.time()


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


def _bearer(request: Request) -> str | None:
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    return value.strip() if scheme.lower() == "bearer" else None


def has_session(request: Request) -> bool:
    return session_valid(request.cookies.get(SESSION_COOKIE), request.app.state.settings.admin_token)


def authenticated(request: Request) -> bool:
    return token_matches(_bearer(request), request.app.state.settings.admin_token) or has_session(request)


def require_token(request: Request) -> None:
    """Dependency cho /api/*: header `Authorization: Bearer <QUILLO_ADMIN_TOKEN>` hoặc cookie phiên của UI."""
    if not authenticated(request):
        raise HTTPException(status_code=401, detail="Cần token", headers={"WWW-Authenticate": "Bearer"})
