import psycopg
import pytest

from quillo import db
from quillo.config import PRODUCT_DIR

MIGRATIONS = PRODUCT_DIR / "migrations"


def columns(conn) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents'")}


def test_migration_0002_idempotent(database_url):
    with psycopg.connect(database_url) as conn:
        assert db.migrate(conn, MIGRATIONS, target=1) == [1]
        assert "tags" not in columns(conn)
        assert db.migrate(conn, MIGRATIONS, target=2) == [2]
        assert "tags" in columns(conn)
        assert db.migrate(conn, MIGRATIONS, target=2) == []
        conn.execute((MIGRATIONS / "0002_v1_1_tags.sql").read_text())
        conn.commit()
        versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
        assert versions == [1, 2]
        assert db.current_schema(conn) == 2


def test_migration_files_are_numbered():
    names = sorted(p.name for p in MIGRATIONS.glob("*.sql"))
    assert names == ["0001_init.sql", "0002_v1_1_tags.sql"]


def test_schema_for_release():
    assert db.schema_for("1.0.0") == 1
    assert db.schema_for("1.1.0") == 2
    with pytest.raises(ValueError):
        db.schema_for("9.9.9")
