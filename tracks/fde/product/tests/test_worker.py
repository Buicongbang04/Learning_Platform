import os
import threading
import time

import psycopg
import pytest

import testkit
from quillo import db, ingest
from quillo.config import PRODUCT_DIR
from quillo_support import make_settings

TEXT = "This agreement is governed by the law of the State of New York. " * 5


def migrated(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        db.migrate(conn, PRODUCT_DIR / "migrations", target=2)


def make_old(*paths) -> None:
    past = time.time() - 60
    for path in paths:
        os.utime(path, (past, past), follow_symlinks=False)


def run_worker(settings, inbox, until, interval: float = 0.1, timeout: float = 30) -> None:
    stop = threading.Event()
    worker = threading.Thread(target=ingest.watch, args=(settings, inbox, interval, stop))
    worker.start()
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not until():
            time.sleep(0.05)
    finally:
        stop.set()
        worker.join(timeout=10)


def test_worker_moves_files_to_done_and_failed(database_url, fake_llm, tmp_path):
    migrated(database_url)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "nda.txt").write_text(TEXT)
    (inbox / "tool.exe").write_bytes(b"MZ")
    (inbox / "huge.txt").write_text("a" * (1024 * 1024 + 1))
    (tmp_path / "secret.txt").write_text(TEXT)
    (inbox / "link.txt").symlink_to(tmp_path / "secret.txt")
    make_old(*inbox.iterdir())
    settings = make_settings(database_url, fake_llm.url, max_upload_mb=1)
    run_worker(settings, inbox, lambda: len(list(inbox.glob("*/*"))) >= 4)
    assert sorted(p.name for p in (inbox / "done").iterdir()) == ["nda.txt"]
    assert sorted(p.name for p in (inbox / "failed").iterdir()) == ["huge.txt", "link.txt", "tool.exe"]
    with psycopg.connect(database_url) as conn:
        assert [r[0] for r in conn.execute("SELECT filename FROM documents")] == ["nda.txt"]


def test_worker_refuses_unwritable_inbox(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root ghi được mọi thư mục")
    settings = make_settings("postgresql://unused/db", "http://127.0.0.1:9")
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    inbox.chmod(0o555)
    try:
        with pytest.raises(ingest.InboxNotWritable, match="không"):
            ingest.watch(settings, inbox, 0.1, threading.Event())
        (inbox).chmod(0o755)
        (inbox / "done").mkdir()
        (inbox / "done").chmod(0o555)
        with pytest.raises(ingest.InboxNotWritable, match="done"):
            ingest.watch(settings, inbox, 0.1, threading.Event())
    finally:
        for path in (inbox, inbox / "done"):
            if path.exists():
                path.chmod(0o755)
    with pytest.raises(ingest.InboxNotWritable, match="không tồn tại"):
        ingest.watch(settings, tmp_path / "missing", 0.1, threading.Event())


def test_worker_main_exits_nonzero_on_bad_inbox(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLO_DATABASE_URL", "postgresql://unused/db")
    monkeypatch.setenv("QUILLO_ADMIN_TOKEN", "x" * 20)
    assert ingest.main(["--watch", str(tmp_path / "missing")]) == 2
    assert "không tồn tại" in capsys.readouterr().err


def test_worker_skips_files_still_being_copied(database_url, fake_llm, tmp_path):
    migrated(database_url)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "copying.txt").write_text(TEXT)
    settings = make_settings(database_url, fake_llm.url)
    run_worker(settings, inbox, lambda: False, interval=1.0, timeout=1.0)
    assert (inbox / "copying.txt").exists()
    assert fake_llm.embedded == []
    make_old(inbox / "copying.txt")
    run_worker(settings, inbox, lambda: (inbox / "done" / "copying.txt").exists(), interval=1.0)
    assert (inbox / "done" / "copying.txt").exists()


def test_worker_leaves_file_when_model_server_down(database_url, tmp_path):
    migrated(database_url)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "nda.txt").write_text(TEXT)
    make_old(inbox / "nda.txt")
    dead = f"http://127.0.0.1:{testkit.free_port()}"
    run_worker(make_settings(database_url, dead), inbox, lambda: False, timeout=1.0)
    assert (inbox / "nda.txt").exists()
    assert list((inbox / "failed").iterdir()) == [] and list((inbox / "done").iterdir()) == []


def test_worker_does_not_overwrite_on_collision(database_url, fake_llm, tmp_path):
    migrated(database_url)
    inbox = tmp_path / "inbox"
    (inbox / "done").mkdir(parents=True)
    (inbox / "done" / "nda.txt").write_text("older")
    (inbox / "nda.txt").write_text(TEXT)
    make_old(inbox / "nda.txt")
    run_worker(make_settings(database_url, fake_llm.url), inbox, lambda: not (inbox / "nda.txt").exists())
    assert sorted(p.name for p in (inbox / "done").iterdir()) == ["nda-1.txt", "nda.txt"]
    assert (inbox / "done" / "nda.txt").read_text() == "older"


def test_read_regular_refuses_swapped_symlink_and_fifo(tmp_path):
    target = tmp_path / "secret.txt"
    target.write_text("secret")
    path = tmp_path / "doc.txt"
    path.write_text("ok")
    assert ingest.read_regular(path, 100) == b"ok"
    path.unlink()
    path.symlink_to(target)
    with pytest.raises(ingest.NotRegularFile):
        ingest.read_regular(path, 100)
    fifo = tmp_path / "pipe.txt"
    os.mkfifo(fifo)
    with pytest.raises(ingest.NotRegularFile):
        ingest.read_regular(fifo, 100)
    big = tmp_path / "big.txt"
    big.write_bytes(b"a" * 101)
    with pytest.raises(ingest.TooLarge):
        ingest.read_regular(big, 100)


def test_classify_errors():
    import httpx

    request = httpx.Request("POST", "http://embed/v1/embeddings")
    assert ingest.classify(httpx.ConnectError("refused", request=request)) == "outage"
    assert ingest.classify(httpx.ReadTimeout("slow", request=request)) == "outage"
    for status, kind in ((400, "fail"), (413, "fail"), (500, "retry"), (503, "retry")):
        error = httpx.HTTPStatusError("x", request=request, response=httpx.Response(status, request=request))
        assert ingest.classify(error) == kind
    assert ingest.classify(psycopg.OperationalError("connection refused")) == "outage"
    assert ingest.classify(psycopg.errors.AdminShutdown("bye")) == "outage"
    assert ingest.classify(psycopg.errors.ProgramLimitExceeded("row too big")) == "fail"
    assert ingest.classify(ingest.UnsupportedType("x")) == "fail"


def test_worker_poison_file_does_not_block_queue(database_url, fake_llm, tmp_path):
    migrated(database_url)
    fake_llm.reject = {"POISON": 400}
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a_poison.txt").write_text("POISON " + TEXT)
    (inbox / "b_ok.txt").write_text(TEXT)
    make_old(*inbox.iterdir())
    run_worker(make_settings(database_url, fake_llm.url), inbox, lambda: len(list(inbox.glob("*/*"))) >= 2)
    assert [p.name for p in (inbox / "failed").iterdir()] == ["a_poison.txt"]
    assert [p.name for p in (inbox / "done").iterdir()] == ["b_ok.txt"]


def test_worker_retries_server_errors_then_gives_up(database_url, fake_llm, tmp_path):
    migrated(database_url)
    fake_llm.reject = {"FLAKY": 500}
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a_flaky.txt").write_text("FLAKY " + TEXT)
    (inbox / "b_ok.txt").write_text(TEXT)
    make_old(*inbox.iterdir())
    run_worker(make_settings(database_url, fake_llm.url), inbox, lambda: (inbox / "failed" / "a_flaky.txt").exists())
    assert (inbox / "done" / "b_ok.txt").exists()
    assert (inbox / "failed" / "a_flaky.txt").exists()
    attempts = [text for text in fake_llm.embedded if "FLAKY" in text and text.startswith("search_document: FLAKY")]
    assert len(attempts) == ingest.MAX_FILE_RETRIES


def test_worker_survives_failed_moves(database_url, fake_llm, tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root ghi được mọi thư mục")
    migrated(database_url)
    fake_llm.reject = {"POISON": 400}
    inbox = tmp_path / "inbox"
    for folder in ("done", "failed"):
        (inbox / folder).mkdir(parents=True)
    (inbox / "a_poison.txt").write_text("POISON " + TEXT)
    (inbox / "b_ok.txt").write_text(TEXT)
    make_old(*[p for p in inbox.iterdir() if p.is_file()])
    settings = make_settings(database_url, fake_llm.url)
    stop = threading.Event()
    original_check = ingest.check_inbox

    def check_then_lock(path):
        original_check(path)
        (inbox / "done").chmod(0o555)
        (inbox / "failed").chmod(0o555)

    worker = threading.Thread(target=ingest.watch, args=(settings, inbox, 0.1, stop))
    try:
        ingest.check_inbox = check_then_lock
        worker.start()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with psycopg.connect(database_url) as conn:
                if conn.execute("SELECT count(*) FROM documents").fetchone()[0]:
                    break
            time.sleep(0.1)
        time.sleep(1.0)
        assert worker.is_alive()
    finally:
        stop.set()
        worker.join(timeout=10)
        ingest.check_inbox = original_check
        (inbox / "done").chmod(0o755)
        (inbox / "failed").chmod(0o755)
    assert sorted(p.name for p in inbox.iterdir() if p.is_file()) == ["a_poison.txt", "b_ok.txt"]
    assert list((inbox / "failed").iterdir()) == [] and list((inbox / "done").iterdir()) == []
    ok_embeds = [t for t in fake_llm.embedded if t.startswith("search_document: This agreement")]
    assert 0 < len(ok_embeds) <= 1 * len(ingest.chunk(TEXT))
