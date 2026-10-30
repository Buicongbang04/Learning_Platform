"""Helper gọi API Metabase / Superset từ máy host (dùng trong bài tập module 10).

    from setup.bi.clients import metabase_session, superset_session   # hoặc thêm setup/bi vào sys.path

    mb = metabase_session()                 # requests.Session đã đăng nhập, đường dẫn tương đối nối vào base_url
    mb.get("/api/database").json()
    ss = superset_session()                 # đã đăng nhập (JWT) + header X-CSRFToken
    ss.get("/api/v1/database/").json()

Cổng đọc từ biến môi trường / setup/.env giống testkit.py (METABASE_PORT, SUPERSET_PORT).
Lần đầu Metabase chưa có admin: `metabase_session()` tự tạo admin (xem METABASE_ADMIN_*).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import testkit  # noqa: E402  (nạp setup/.env và bảng cổng)

METABASE_ADMIN_EMAIL = os.environ.get("METABASE_ADMIN_EMAIL", "admin@example.com")
METABASE_ADMIN_PASSWORD = os.environ.get("METABASE_ADMIN_PASSWORD", "DeLearning-Admin1")
SUPERSET_ADMIN_USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
SUPERSET_ADMIN_PASSWORD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")

# Postgres nhìn từ trong mạng Docker (de-net): host `postgres`, cổng 5432.
PG_DOCKER = {"host": "postgres", "port": 5432, "dbname": "de", "user": "de", "password": "de"}


class _Session(requests.Session):
    """requests.Session nhận đường dẫn tương đối (`/api/...`) và nối vào `base_url`."""

    base_url = ""

    def request(self, method, url, *args, **kwargs):  # type: ignore[override]
        if url.startswith("/"):
            url = self.base_url + url
        kwargs.setdefault("timeout", 60)
        return super().request(method, url, *args, **kwargs)


def base_url(name: str) -> str:
    host = os.environ.get(testkit.SERVICES[name][0], testkit.SERVICES[name][1])
    return f"http://{host}:{testkit._port(name)}"


def metabase_setup_admin(session: requests.Session | None = None) -> bool:
    """Tạo admin Metabase nếu chưa setup. Trả True nếu vừa tạo, False nếu đã có sẵn."""
    s = session or _Session()
    if isinstance(s, _Session) and not s.base_url:
        s.base_url = base_url("metabase")
    # Metabase vẫn trả setup-token một lúc sau khi setup xong: thử đăng nhập trước để biết admin đã có chưa.
    login = s.post("/api/session", json={"username": METABASE_ADMIN_EMAIL, "password": METABASE_ADMIN_PASSWORD})
    if login.ok:
        return False
    token = s.get("/api/session/properties").json().get("setup-token")
    if not token:
        raise RuntimeError(
            "Metabase đã setup với tài khoản khác. Đặt METABASE_ADMIN_EMAIL / METABASE_ADMIN_PASSWORD "
            "cho khớp, hoặc xoá volume de-learning_metabase_data để setup lại."
        )
    r = s.post(
        "/api/setup",
        json={
            "token": token,
            "user": {
                "email": METABASE_ADMIN_EMAIL,
                "password": METABASE_ADMIN_PASSWORD,
                "first_name": "Admin",
                "last_name": "User",
                "site_name": "DE Learning",
            },
            "prefs": {"site_name": "DE Learning", "site_locale": "en", "allow_tracking": False},
        },
    )
    r.raise_for_status()
    return True


def metabase_session() -> requests.Session:
    """Session Metabase đã đăng nhập (header X-Metabase-Session). Tự setup admin nếu mới bật lần đầu."""
    s = _Session()
    s.base_url = base_url("metabase")
    metabase_setup_admin(s)
    r = s.post("/api/session", json={"username": METABASE_ADMIN_EMAIL, "password": METABASE_ADMIN_PASSWORD})
    r.raise_for_status()
    s.headers["X-Metabase-Session"] = r.json()["id"]
    return s


def superset_session() -> requests.Session:
    """Session Superset đã đăng nhập: Bearer JWT + X-CSRFToken (cookie phiên giữ trong Session)."""
    s = _Session()
    s.base_url = base_url("superset")
    r = s.post(
        "/api/v1/security/login",
        json={"username": SUPERSET_ADMIN_USER, "password": SUPERSET_ADMIN_PASSWORD, "provider": "db", "refresh": True},
    )
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    c = s.get("/api/v1/security/csrf_token/")
    c.raise_for_status()
    s.headers["X-CSRFToken"] = c.json()["result"]
    s.headers["Referer"] = s.base_url
    return s
