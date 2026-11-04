import logging
import re
from pathlib import Path

import psycopg

log = logging.getLogger(__name__)

SCHEMA_FOR_RELEASE = {"1.0.0": 1, "1.1.0": 2}
MIGRATION_FILE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
MIGRATION_LOCK = 4_242_001


def schema_for(version: str) -> int:
    if version not in SCHEMA_FOR_RELEASE:
        raise ValueError(f"Không biết schema của bản {version}; các bản đã phát hành: {', '.join(SCHEMA_FOR_RELEASE)}")
    return SCHEMA_FOR_RELEASE[version]


def connect(database_url: str, timeout: int = 5) -> psycopg.Connection:
    return psycopg.connect(database_url, connect_timeout=timeout)


def migration_files(directory: Path, target: int) -> list[tuple[int, Path]]:
    found = []
    for path in sorted(Path(directory).glob("*.sql")):
        match = MIGRATION_FILE.match(path.name)
        if match and int(match.group(1)) <= target:
            found.append((int(match.group(1)), path))
    return found


def current_schema(conn: psycopg.Connection) -> int:
    exists = conn.execute("SELECT to_regclass('schema_migrations') IS NOT NULL").fetchone()[0]
    if not exists:
        return 0
    return conn.execute("SELECT coalesce(max(version), 0) FROM schema_migrations").fetchone()[0]


def migrate(conn: psycopg.Connection, directory: Path, target: int) -> list[int]:
    """Áp các migration số <= target chưa có trong schema_migrations (một transaction, khoá advisory); trả các số vừa áp."""
    conn.commit()
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK,))
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "version integer PRIMARY KEY, name text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        applied = []
        for number, path in migration_files(directory, target):
            if number in done:
                continue
            log.info("áp migration", extra={"fields": {"migration": path.name}})
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations (version, name) VALUES (%s, %s)", (number, path.name))
            applied.append(number)
        newest = max(done | set(applied), default=0)
    if newest > target:
        log.warning("schema mới hơn bản đang chạy", extra={"fields": {"schema": newest, "expected": target}})
    return applied


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7g}" for v in values) + "]"


def save_document(conn: psycopg.Connection, doc_id: str, filename: str, size: int, chunks: list[str],
                  embeddings: list[list[float]], tags: list[str] | None) -> None:
    with conn.transaction():
        conn.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        if tags is None:
            conn.execute("INSERT INTO documents (id, filename, size_bytes) VALUES (%s, %s, %s)",
                         (doc_id, filename, size))
        else:
            conn.execute("INSERT INTO documents (id, filename, size_bytes, tags) VALUES (%s, %s, %s, %s)",
                         (doc_id, filename, size, tags))
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO chunks (doc_id, chunk, text, embedding) VALUES (%s, %s, %s, %s::vector)",
                            [(doc_id, i, text, vector_literal(vec)) for i, (text, vec) in enumerate(zip(chunks, embeddings))])


LIST_SQL = ("SELECT d.id, d.filename, d.size_bytes, d.created_at, count(c.chunk), {tags} FROM documents d "
            "LEFT JOIN chunks c ON c.doc_id = d.id GROUP BY d.id ORDER BY d.created_at DESC")
LIST_V1_0 = LIST_SQL.format(tags="NULL")
LIST_V1_1 = LIST_SQL.format(tags="d.tags")


def list_documents(conn: psycopg.Connection, with_tags: bool) -> list[dict]:
    documents = []
    for doc_id, filename, size, created, chunks, tags in conn.execute(LIST_V1_1 if with_tags else LIST_V1_0):
        item = {"doc_id": doc_id, "filename": filename, "size_bytes": size, "chunks": chunks,
                "created_at": created.isoformat()}
        if with_tags:
            item["tags"] = tags
        documents.append(item)
    return documents


def search(conn: psycopg.Connection, embedding: list[float], top_k: int) -> list[dict]:
    rows = conn.execute(
        "SELECT c.doc_id, c.chunk, c.text, d.filename FROM chunks c JOIN documents d ON d.id = c.doc_id "
        "ORDER BY c.embedding <=> %s::vector LIMIT %s", (vector_literal(embedding), top_k)).fetchall()
    return [{"doc_id": r[0], "chunk": r[1], "text": r[2], "filename": r[3]} for r in rows]
