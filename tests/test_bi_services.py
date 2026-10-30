"""Kiểm hạ tầng BI cho module 10: Metabase + Superset đăng nhập được và thấy database `de` (schema `da`).

Tắt dịch vụ -> SKIP kèm lệnh bật. Bật rồi mà chưa khởi tạo -> FAIL kèm lệnh khởi tạo.
"""
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "setup" / "bi"))

import testkit  # noqa: E402

START = (
    "docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase superset "
    "&& uv run python setup/bi/load_da.py && uv run python setup/bi/init_bi.py"
)


@pytest.fixture(scope="module", autouse=True)
def need_bi():
    for name in ("postgres", "metabase", "superset"):
        if not testkit.service_up(name):
            pytest.skip(f"Dịch vụ {name} chưa chạy. Bật BI bằng: {START}")


@pytest.fixture(scope="module")
def metabase():
    import clients

    try:
        return clients.metabase_session()
    except RuntimeError as e:
        pytest.skip(str(e))


@pytest.fixture(scope="module")
def superset():
    import clients

    return clients.superset_session()


def test_metabase_login_va_thay_database_de(metabase):
    me = metabase.get("/api/user/current")
    assert me.ok and me.json()["email"] == "admin@example.com"
    dbs = metabase.get("/api/database").json()
    dbs = dbs["data"] if isinstance(dbs, dict) else dbs
    de = [d for d in dbs if d["name"] == "de"]
    assert de, f"Metabase chưa có database `de`. Chạy: uv run python setup/bi/init_bi.py"
    end = time.time() + 60
    schemas: list = []
    while time.time() < end:  # sync schema chạy nền sau khi thêm database
        schemas = metabase.get(f"/api/database/{de[0]['id']}/schemas").json()
        if "da" in schemas:
            break
        time.sleep(3)
    assert "da" in schemas, "Metabase không thấy schema `da`. Chạy: uv run python setup/bi/load_da.py"


def test_superset_login_va_thay_database_de(superset):
    r = superset.get("/api/v1/database/")
    assert r.ok
    de = [d for d in r.json()["result"] if d["database_name"] == "de"]
    assert de, "Superset chưa có database `de`. Chạy: uv run python setup/bi/init_bi.py"
    schemas = superset.get(f"/api/v1/database/{de[0]['id']}/schemas/")
    assert schemas.ok
    assert "da" in schemas.json()["result"], "Superset không thấy schema `da`. Chạy: uv run python setup/bi/load_da.py"


def test_bang_da_co_dong(metabase):
    de = [d for d in (lambda r: r["data"] if isinstance(r, dict) else r)(metabase.get("/api/database").json()) if d["name"] == "de"]
    assert de, "Chưa có database `de`. Chạy: uv run python setup/bi/init_bi.py"
    q = {"database": de[0]["id"], "type": "native", "native": {"query": ""}}
    for t in ("online_retail_ii", "bike_hour"):
        q["native"]["query"] = f"SELECT count(*) FROM da.{t}"
        r = metabase.post("/api/dataset", json=q).json()
        assert r["data"]["rows"][0][0] > 0, f"da.{t} rỗng. Chạy: uv run python setup/bi/load_da.py"
