import os
import stat
import subprocess
import time

import psycopg
import pytest

import release
import testkit
from quillo import db
from quillo.config import PRODUCT_DIR

OPS = PRODUCT_DIR / "ops"
PASSWORD = "backup-test-only"


@pytest.fixture
def pg():
    if not testkit.docker_ready():
        pytest.skip("Cần Docker đang chạy để dựng Postgres/pgvector (testkit.DockerLab)")
    testkit.Exercise.require_image(release.IMAGES["db"])
    with testkit.DockerLab() as lab:
        lab.start("db", release.IMAGES["db"], ports=(5432,), memory="512m",
                  env={"POSTGRES_USER": "quillo", "POSTGRES_DB": "quillo", "POSTGRES_PASSWORD": PASSWORD})
        url = f"postgresql://quillo:{PASSWORD}@127.0.0.1:{lab.port('db', 5432)}/quillo"
        deadline = time.monotonic() + 60
        while True:
            try:
                with psycopg.connect(url, connect_timeout=2) as conn:
                    conn.execute("SELECT 1")
                if lab.exec("db", "pg_isready", "-U", "quillo", "-h", "/var/run/postgresql").returncode == 0:
                    break
            except psycopg.OperationalError:
                pass
            if time.monotonic() > deadline:
                pytest.fail(f"Postgres không sẵn sàng. Log:\n{lab.logs('db')[-2000:]}")
            time.sleep(0.5)
        yield url, f"docker exec -i {lab.name('db')}"


def seed(url: str, count: int) -> None:
    with psycopg.connect(url) as conn:
        db.migrate(conn, PRODUCT_DIR / "migrations", target=2)
        for i in range(count):
            vectors = [[float(i + j) / 1000] * 768 for j in range(3)]
            db.save_document(conn, f"doc{i:013d}", f"legal/nda-{i}.txt", 100, [f"chunk {i}-{j}" for j in range(3)],
                             vectors, ["nda"])


def counts(url: str) -> tuple[int, int]:
    with psycopg.connect(url) as conn:
        return (conn.execute("SELECT count(*) FROM documents").fetchone()[0],
                conn.execute("SELECT count(*) FROM chunks").fetchone()[0])


def ops(script: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", str(OPS / script), *args], capture_output=True, text=True, timeout=120,
                          env={**os.environ, **(env or {})})


def test_backup_restore_roundtrip(pg, tmp_path):
    url, exec_prefix = pg
    seed(url, 4)
    dest = tmp_path / "backups"
    made = ops("backup.sh", "--exec", exec_prefix, str(dest))
    assert made.returncode == 0, made.stdout + made.stderr
    dump = dest / made.stdout.strip().splitlines()[-1].rsplit("/", 1)[-1]
    assert dump.is_file() and dump.suffix == ".dump" and dump.read_bytes()[:5] == b"PGDMP"
    assert stat.S_IMODE(dump.stat().st_mode) == 0o600
    assert stat.S_IMODE(dest.stat().st_mode) == 0o700
    checksum = dump.with_name(dump.name + ".sha256")
    assert checksum.read_text().split() == [release.sha256(dump), dump.name]

    refused = ops("restore.sh", "--exec", exec_prefix, str(dump))
    assert refused.returncode != 0 and "--force" in refused.stderr
    assert counts(url) == (4, 12)

    with psycopg.connect(url) as conn:
        conn.execute("DELETE FROM documents WHERE id <> 'doc0000000000000'")
        conn.execute("INSERT INTO documents (id, filename, size_bytes) VALUES ('extra', 'x.txt', 1)")
    forced = ops("restore.sh", "--force", "--exec", exec_prefix, str(dump))
    assert forced.returncode == 0, forced.stdout + forced.stderr
    assert counts(url) == (4, 12)
    with psycopg.connect(url) as conn:
        assert conn.execute("SELECT max(version) FROM schema_migrations").fetchone()[0] == 2
        names = [r[0] for r in conn.execute("SELECT filename FROM documents ORDER BY id")]
    assert names == [f"legal/nda-{i}.txt" for i in range(4)]

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP TABLE chunks, documents, schema_migrations")
    fresh = ops("restore.sh", "--exec", exec_prefix, str(dump))
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr
    assert counts(url) == (4, 12)


def test_backup_refuses_low_disk_and_restore_checks_sha(pg, tmp_path):
    url, exec_prefix = pg
    seed(url, 1)
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "df").write_text("#!/bin/sh\necho 'Filesystem 1024-blocks Used Available Capacity Mounted on'\n"
                             "echo '/dev/x 100 99 1 99% /'\n")
    (fake / "df").chmod(0o755)
    low = ops("backup.sh", "--exec", exec_prefix, str(tmp_path / "b"), env={"PATH": f"{fake}:{os.environ['PATH']}"})
    assert low.returncode != 0 and "trống" in low.stderr
    assert not list((tmp_path / "b").glob("*.dump"))
    made = ops("backup.sh", "--exec", exec_prefix, str(tmp_path / "b"))
    dump = next((tmp_path / "b").glob("*.dump"))
    with open(dump, "r+b") as handle:
        handle.seek(-1, os.SEEK_END)
        last = handle.read(1)
        handle.seek(-1, os.SEEK_END)
        handle.write(bytes([last[0] ^ 1]))
    bad = ops("restore.sh", "--force", "--exec", exec_prefix, str(dump))
    assert bad.returncode != 0 and "sha256" in bad.stderr
    assert made.returncode == 0
    assert ops("backup.sh", "--exec", exec_prefix).returncode == 2
    assert ops("restore.sh", "--bogus", str(dump)).returncode == 2


def test_ops_scripts_are_posix_and_know_runtimes():
    for name in ("backup.sh", "restore.sh"):
        text = (OPS / name).read_text()
        assert text.startswith("#!/bin/sh\n")
        assert subprocess.run(["sh", "-n", str(OPS / name)]).returncode == 0
        for runtime in ("--compose", "--kubectl", "--exec"):
            assert runtime in text
        help_text = ops(name, "--help")
        assert help_text.returncode == 0 and "kubectl exec" in help_text.stdout
