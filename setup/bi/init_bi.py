"""Khởi tạo Metabase + Superset (chạy lại nhiều lần không sao):

    uv run python setup/bi/init_bi.py

- Metabase: tạo admin (admin@example.com) nếu chưa setup, thêm database Postgres `de`.
- Superset: admin/admin do container tự tạo; thêm database Postgres `de`.
Hai công cụ đều nối Postgres bằng host `postgres:5432` (mạng Docker), đọc schema `da`
(nạp bằng `uv run python setup/bi/load_da.py`).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clients  # noqa: E402

DB_NAME = "de"


def init_metabase() -> None:
    created = clients.metabase_setup_admin()
    print("Metabase: " + ("đã tạo admin" if created else "admin đã có"))
    s = clients.metabase_session()
    dbs = s.get("/api/database").json()
    dbs = dbs["data"] if isinstance(dbs, dict) else dbs
    if any(d["name"] == DB_NAME for d in dbs):
        print(f"Metabase: database `{DB_NAME}` đã có")
        return
    r = s.post(
        "/api/database",
        json={
            "name": DB_NAME,
            "engine": "postgres",
            "details": {
                "host": clients.PG_DOCKER["host"],
                "port": clients.PG_DOCKER["port"],
                "dbname": clients.PG_DOCKER["dbname"],
                "user": clients.PG_DOCKER["user"],
                "password": clients.PG_DOCKER["password"],
                "ssl": False,
            },
            "is_full_sync": True,
        },
    )
    r.raise_for_status()
    print(f"Metabase: đã thêm database `{DB_NAME}` (id={r.json()['id']})")


def init_superset() -> None:
    s = clients.superset_session()
    existing = s.get("/api/v1/database/", params={"q": '(filters:!((col:database_name,opr:eq,value:%s)))' % DB_NAME}).json()
    if existing.get("count"):
        print(f"Superset: database `{DB_NAME}` đã có")
        return
    p = clients.PG_DOCKER
    r = s.post(
        "/api/v1/database/",
        json={
            "database_name": DB_NAME,
            "sqlalchemy_uri": f"postgresql+psycopg2://{p['user']}:{p['password']}@{p['host']}:{p['port']}/{p['dbname']}",
            "expose_in_sqllab": True,
        },
    )
    r.raise_for_status()
    print(f"Superset: đã thêm database `{DB_NAME}` (id={r.json()['id']})")


def wait(name: str, timeout: int = 300) -> None:
    import requests

    url = clients.base_url(name) + ("/api/health" if name == "metabase" else "/health")
    end = time.time() + timeout
    while time.time() < end:
        try:
            if requests.get(url, timeout=3).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise SystemExit(f"{name} chưa sẵn sàng sau {timeout}s ({url}). Xem: docker compose -f setup/docker-compose.yml logs {name}")


if __name__ == "__main__":
    wait("metabase")
    wait("superset")
    init_metabase()
    init_superset()
