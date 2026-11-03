import hashlib
import hmac

from fastapi import HTTPException, Request

SESSION_COOKIE = "quillo_session"
SESSION_MAX_AGE = 8 * 3600


def token_matches(given: str | None, expected: str) -> bool:
    return given is not None and hmac.compare_digest(given.encode(), expected.encode())


def session_value(token: str) -> str:
    return hmac.new(token.encode(), b"quillo-session-v1", hashlib.sha256).hexdigest()


def _bearer(request: Request) -> str | None:
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    return value.strip() if scheme.lower() == "bearer" else None


def has_session(request: Request) -> bool:
    expected = session_value(request.app.state.settings.admin_token)
    return token_matches(request.cookies.get(SESSION_COOKIE), expected)


def authenticated(request: Request) -> bool:
    return token_matches(_bearer(request), request.app.state.settings.admin_token) or has_session(request)


def require_token(request: Request) -> None:
    """Dependency cho /api/*: header `Authorization: Bearer <QUILLO_ADMIN_TOKEN>` hoặc cookie phiên của UI."""
    if not authenticated(request):
        raise HTTPException(status_code=401, detail="Cần token", headers={"WWW-Authenticate": "Bearer"})
