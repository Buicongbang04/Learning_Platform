"""Gửi báo cáo đồng bộ (JSON) tới dịch vụ audit nội bộ của khách bằng token đọc từ tệp (`AUDIT_TOKEN_FILE`)."""

import http.client
import logging
import os
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path

LOG = logging.getLogger("push_report")
TIMEOUT = 15


class ConfigError(Exception):
    pass


class Redact(logging.Filter):
    def __init__(self, secret: str) -> None:
        super().__init__()
        self.secret = secret

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage(), self.secret)
        record.args = None
        return True


def redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


def read_token() -> str:
    if "AUDIT_TOKEN" in os.environ:
        raise ConfigError("AUDIT_TOKEN trong biến môi trường không được nhận; giao token bằng tệp qua AUDIT_TOKEN_FILE")
    name = os.environ.get("AUDIT_TOKEN_FILE")
    if not name:
        raise ConfigError("thiếu AUDIT_TOKEN_FILE (đường dẫn tệp chứa token)")
    path = Path(name)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise ConfigError(f"không mở được tệp token {path}: {error.strerror}") from None
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ConfigError(f"{path} không phải tệp thường")
        if info.st_mode & 0o077:
            raise ConfigError(f"tệp token {path} có quyền {stat.filemode(info.st_mode)}; chỉ chủ tệp được đọc (chmod 600)")
        token = handle.read().decode("utf-8", errors="strict").rstrip("\r\n")
    if not token or any(c.isspace() for c in token):
        raise ConfigError(f"tệp token {path} rỗng hoặc có khoảng trắng")
    return token


def setup_logging(token: str) -> None:
    handler = logging.FileHandler("push_report.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.addFilter(Redact(token))
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)


def send(url: str, token: str, body: bytes) -> int:
    request = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("cách dùng: push_report.py <tệp báo cáo JSON>", file=sys.stderr)
        return 2
    url = os.environ.get("AUDIT_URL", "")
    try:
        if not url.startswith(("http://", "https://")):
            raise ConfigError("thiếu hoặc sai AUDIT_URL")
        token = read_token()
        body = Path(argv[1]).read_bytes()
    except (ConfigError, OSError, UnicodeDecodeError) as error:
        print(f"lỗi cấu hình: {error}", file=sys.stderr)
        return 2
    setup_logging(token)
    LOG.info("gửi %s (%d byte) tới %s", argv[1], len(body), url)
    try:
        status = send(url, token, body)
    except urllib.error.HTTPError as error:
        message = f"dịch vụ audit trả HTTP {error.code} {error.reason}"
        error.close()
    except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
        reason = getattr(error, "reason", error)
        message = f"không gửi được tới {url}: {type(reason).__name__}: {redact(str(reason), token)}"
    else:
        LOG.info("đã gửi, HTTP %d", status)
        print(f"đã gửi báo cáo, HTTP {status}")
        return 0
    LOG.error(message)
    print(redact(message, token), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
