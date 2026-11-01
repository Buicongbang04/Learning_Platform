from email.utils import parsedate_to_datetime

RETRYABLE_STATUS = {408, 429, 502, 503, 504}
IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


def split_transcript(text: str) -> tuple[list[str], list[str]]:
    """Tách transcript `curl -v` thành (dòng request, dòng response), đã bỏ ký tự `>`/`<` và một dấu cách sau nó.

    Dòng rỗng sau khi bỏ tiền tố (kết thúc phần header) bị bỏ.
    """
    request, response = [], []
    for line in text.splitlines():
        if line[:1] in (">", "<"):
            body = line[2:] if line[1:2] == " " else line[1:]
            if body.strip():
                (request if line[0] == ">" else response).append(body.rstrip())
    return request, response


def headers(lines: list[str]) -> dict[str, str]:
    """Header sau dòng đầu, tên chữ thường. Header lặp lại thì nối bằng `, `."""
    # TODO
    raise NotImplementedError


def cache_directives(value: str) -> dict[str, str | None]:
    """`public, max-age=60, s-maxage=600` thành {"public": None, "max-age": "60", "s-maxage": "600"}."""
    # TODO
    raise NotImplementedError


def analyze(text: str) -> dict:
    """Trả 8 khoá method, version, status, retry_safe, retry_after, cache, ttl, keep_alive (xem README)."""
    # TODO: dòng đầu request là `METHOD path VERSION`, dòng đầu response là `VERSION status [reason]`
    # TODO: retry_safe, retry_after (giây hoặc HTTP-date so với header Date)
    # TODO: cache và ttl theo đúng thứ tự quy tắc trong README
    # TODO: keep_alive theo phiên bản và header Connection
    raise NotImplementedError
