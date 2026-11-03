import threading
import time

import psycopg

from quillo import db, ingest
from quillo.config import PRODUCT_DIR
from quillo_support import make_settings

TEXT = "This agreement is governed by the law of the State of New York. " * 5


def test_worker_moves_files_to_done_and_failed(database_url, fake_llm, tmp_path):
    with psycopg.connect(database_url) as conn:
        db.migrate(conn, PRODUCT_DIR / "migrations", target=2)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "nda.txt").write_text(TEXT)
    (inbox / "tool.exe").write_bytes(b"MZ")
    (inbox / "huge.txt").write_text("a" * (1024 * 1024 + 1))
    (tmp_path / "secret.txt").write_text(TEXT)
    (inbox / "link.txt").symlink_to(tmp_path / "secret.txt")
    settings = make_settings(database_url, fake_llm.url, max_upload_mb=1)
    stop = threading.Event()
    worker = threading.Thread(target=ingest.watch, args=(settings, inbox, 0.1, stop))
    worker.start()
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and len(list(inbox.glob("*/*"))) < 3:
            time.sleep(0.1)
    finally:
        stop.set()
        worker.join(timeout=10)
    assert sorted(p.name for p in (inbox / "done").iterdir()) == ["nda.txt"]
    assert sorted(p.name for p in (inbox / "failed").iterdir()) == ["huge.txt", "tool.exe"]
    assert (inbox / "link.txt").is_symlink()
    with psycopg.connect(database_url) as conn:
        assert [r[0] for r in conn.execute("SELECT filename FROM documents")] == ["nda.txt"]
