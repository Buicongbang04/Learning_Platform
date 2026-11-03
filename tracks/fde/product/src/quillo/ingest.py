"""Nạp tài liệu: trích văn bản (TXT/HTML/PDF), cắt đoạn, embed, ghi Postgres. Chạy `python -m quillo.ingest --watch DIR`."""

import argparse
import hashlib
import io
import logging
import os
import re
import signal
import stat
import sys
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

import httpx
import psycopg

from quillo import db, rag
from quillo.config import Settings, setup_logging
from quillo.llm import ModelServer

log = logging.getLogger("quillo.ingest")

SUPPORTED = {".txt", ".md", ".html", ".htm", ".pdf"}
UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._ -]+")
MAX_FILENAME = 200
MAX_BACKOFF_S = 60.0
TRANSIENT = (httpx.HTTPError, psycopg.OperationalError)


class UnsupportedType(ValueError):
    pass


class EmptyDocument(ValueError):
    pass


class TooLarge(ValueError):
    pass


class NotRegularFile(ValueError):
    pass


class InboxNotWritable(RuntimeError):
    pass


def safe_filename(raw: str) -> str:
    name = UNSAFE_CHARS.sub("_", Path(raw.replace("\\", "/")).name).lstrip(" .-").rstrip(" .")
    if not name:
        return "document"
    if len(name) > MAX_FILENAME:
        suffix = Path(name).suffix[:16]
        name = name[:MAX_FILENAME - len(suffix)] + suffix
    return name


def document_id(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


class _HTMLText(HTMLParser):
    SKIP = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag in self.SKIP:
            self._skipping += 1

    def handle_endtag(self, tag) -> None:
        if tag in self.SKIP and self._skipping:
            self._skipping -= 1

    def handle_data(self, data) -> None:
        if not self._skipping:
            self.parts.append(data)


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise UnsupportedType(f"Không hỗ trợ loại tệp {suffix or '(không đuôi)'}; nhận: {', '.join(sorted(SUPPORTED))}")
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    text = data.decode("utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        parser = _HTMLText()
        parser.feed(text)
        parser.close()
        return " ".join(parser.parts)
    return text


def chunk(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    """Cắt theo từ thành đoạn <= size ký tự; đoạn sau lặp lại khoảng `overlap` ký tự cuối của đoạn trước."""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end, length = start, 0
        while end < len(words) and length + len(words[end]) + (end > start) <= size:
            length += len(words[end]) + (end > start)
            end += 1
        end = max(end, start + 1)
        chunks.append(" ".join(words[start:end])[:size])
        if end >= len(words):
            break
        back, kept = end, 0
        while back > start + 1 and kept + len(words[back - 1]) + 1 <= overlap:
            back -= 1
            kept += len(words[back]) + 1
        start = back
    return chunks


def ingest_bytes(conn, embedder: ModelServer, filename: str, data: bytes, *, max_bytes: int,
                 tags: list[str] | None = None) -> dict:
    if len(data) > max_bytes:
        raise TooLarge(f"{filename}: {len(data)} byte, vượt giới hạn {max_bytes} byte")
    pieces = chunk(extract_text(filename, data))
    if not pieces:
        raise EmptyDocument(f"{filename}: không trích được chữ nào (PDF scan cần OCR trước)")
    doc_id = document_id(data)
    db.save_document(conn, doc_id, filename, len(data), pieces, rag.embed_documents(embedder, pieces), tags)
    log.info("đã nạp tài liệu", extra={"fields": {"doc_id": doc_id, "filename": filename, "chunks": len(pieces)}})
    return {"doc_id": doc_id, "filename": filename, "chunks": len(pieces)}


def read_regular(path: Path, max_bytes: int) -> bytes:
    """Đọc tệp thường, không theo symlink (O_NOFOLLOW + fstat trên chính fd đã mở, tránh TOCTOU), tối đa max_bytes."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        if os.path.islink(path):
            raise NotRegularFile(f"{path.name}: là symlink, không nạp") from error
        raise
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise NotRegularFile(f"{path.name}: không phải tệp thường")
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise TooLarge(f"{path.name}: vượt giới hạn {max_bytes} byte")
    return data


def _move(path: Path, folder: str) -> Path:
    target_dir = path.parent / folder
    target = target_dir / path.name
    n = 1
    while target.exists() or target.is_symlink():
        target = target_dir / f"{path.stem}-{n}{path.suffix}"
        n += 1
    path.rename(target)
    return target


def check_inbox(inbox: Path) -> None:
    """Inbox, `done/`, `failed/` phải tồn tại và ghi được với user của worker, nếu không worker nạp lại mãi một tệp."""
    if not inbox.is_dir():
        raise InboxNotWritable(f"Inbox {inbox} không tồn tại hoặc không phải thư mục")
    for folder in (inbox, inbox / "done", inbox / "failed"):
        try:
            folder.mkdir(exist_ok=True)
        except OSError as error:
            raise InboxNotWritable(f"Không tạo được {folder} ({error.strerror}); worker chạy uid {os.getuid()}") from error
        if not os.access(folder, os.W_OK | os.X_OK):
            raise InboxNotWritable(f"{folder} không ghi được với uid {os.getuid()}; "
                                   f"cấp quyền ghi cho uid này trên thư mục inbox phía host")


def _settled(path: Path, settle_s: float) -> bool:
    try:
        return time.time() - path.lstat().st_mtime >= settle_s
    except OSError:
        return False


def watch(settings: Settings, inbox: Path, interval: float = 5.0, stop: threading.Event | None = None) -> None:
    """Quét `inbox` định kỳ: nạp xong chuyển vào `done/`, lỗi của chính tệp chuyển vào `failed/`.

    Bỏ qua tệp sửa đổi chưa quá 2 chu kỳ quét (có thể đang được chép vào). Lỗi tạm thời (model server, database)
    thì để nguyên tệp và chờ lùi dần tới MAX_BACKOFF_S rồi thử lại. Inbox không ghi được thì dừng ngay (InboxNotWritable).
    """
    stop = stop or threading.Event()
    check_inbox(inbox)
    embedder = ModelServer(settings.embed_url, settings.http_timeout_s)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    settle_s = 2 * interval
    backoff = interval
    log.info("worker bắt đầu theo dõi", extra={"fields": {"inbox": str(inbox), "version": settings.version}})
    while not stop.is_set():
        try:
            files = sorted(p for p in inbox.iterdir()
                           if not p.name.startswith(".") and not p.is_dir() and _settled(p, settle_s))
        except OSError as error:
            log.error("không đọc được inbox", extra={"fields": {"inbox": str(inbox), "error": str(error)}})
            files = []
        wait = interval
        for path in files:
            try:
                data = read_regular(path, max_bytes)
                with db.connect(settings.database_url) as conn:
                    ingest_bytes(conn, embedder, safe_filename(path.name), data, max_bytes=max_bytes)
                _move(path, "done")
                backoff = interval
            except TRANSIENT as error:
                log.warning("lỗi tạm thời, để nguyên tệp và thử lại sau",
                            extra={"fields": {"file": path.name, "error": repr(error), "retry_s": backoff}})
                wait, backoff = backoff, min(backoff * 2, MAX_BACKOFF_S)
                break
            except Exception as error:
                log.error("nạp tài liệu lỗi", extra={"fields": {"file": path.name, "error": repr(error)}})
                _move(path, "failed")
            if stop.is_set():
                break
        stop.wait(wait)
    embedder.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m quillo.ingest", description=__doc__)
    parser.add_argument("--watch", type=Path, help="thư mục inbox cần theo dõi")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("files", nargs="*", type=Path, help="nạp một lần các tệp này rồi thoát")
    args = parser.parse_args(argv)
    setup_logging()
    settings = Settings.from_env()
    if args.watch:
        stop = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stop.set())
        try:
            watch(settings, args.watch, args.interval, stop)
        except InboxNotWritable as error:
            log.error("inbox không dùng được", extra={"fields": {"error": str(error)}})
            print(f"quillo worker: {error}", file=sys.stderr)
            return 2
        return 0
    embedder = ModelServer(settings.embed_url, settings.http_timeout_s)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    failed = 0
    for path in args.files:
        try:
            data = read_regular(path, max_bytes)
            with db.connect(settings.database_url) as conn:
                print(ingest_bytes(conn, embedder, safe_filename(path.name), data, max_bytes=max_bytes))
        except Exception as error:
            failed += 1
            print(f"{path}: {error}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
