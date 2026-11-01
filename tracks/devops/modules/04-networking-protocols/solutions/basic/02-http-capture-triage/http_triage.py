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
    result: dict[str, str] = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        key = name.strip().lower()
        result[key] = f"{result[key]}, {value.strip()}" if key in result else value.strip()
    return result


def cache_directives(value: str) -> dict[str, str | None]:
    """`public, max-age=60, s-maxage=600` thành {"public": None, "max-age": "60", "s-maxage": "600"}."""
    result: dict[str, str | None] = {}
    for part in value.split(","):
        name, sep, arg = part.strip().partition("=")
        if name:
            result[name.strip().lower()] = arg.strip().strip('"') if sep else None
    return result


def seconds_between(later: str, earlier: str) -> int:
    try:
        delta = parsedate_to_datetime(later) - parsedate_to_datetime(earlier)
    except (TypeError, ValueError):
        return 0
    return max(0, int(delta.total_seconds()))


def retry_after(value: str | None, date: str | None) -> int | None:
    if value is None:
        return None
    if value.strip().isdigit():
        return int(value.strip())
    return seconds_between(value, date) if date else None


def cache_state(req: dict[str, str], resp: dict[str, str]) -> tuple[str, int | None]:
    cc = cache_directives(resp.get("cache-control", ""))
    if "no-store" in cc:
        return "no-store", None
    if "private" in cc:
        return "private", None
    if "authorization" in req and not {"public", "s-maxage", "must-revalidate"} & cc.keys():
        return "private", None
    if "no-cache" in cc:
        return "revalidate", None
    if cc.get("s-maxage") is not None:
        lifetime = int(cc["s-maxage"])
    elif cc.get("max-age") is not None:
        lifetime = int(cc["max-age"])
    elif "expires" in resp and "date" in resp:
        lifetime = seconds_between(resp["expires"], resp["date"])
    else:
        return "none", None
    remaining = lifetime - int(resp.get("age", "0") or 0)
    return ("fresh", remaining) if remaining > 0 else ("stale", 0)


def keep_alive(version: str, resp: dict[str, str]) -> bool:
    tokens = {t.strip().lower() for t in resp.get("connection", "").split(",")}
    if version in ("HTTP/2", "HTTP/3"):
        return True
    if version == "HTTP/1.0":
        return "keep-alive" in tokens
    return "close" not in tokens


def analyze(text: str) -> dict:
    """Trả 8 khoá method, version, status, retry_safe, retry_after, cache, ttl, keep_alive (xem README)."""
    request, response = split_transcript(text)
    method = request[0].split()[0].upper()
    version, status_text, *_ = response[0].split()
    status = int(status_text)
    req, resp = headers(request), headers(response)
    cache, ttl = cache_state(req, resp)
    return {
        "method": method,
        "version": version.upper(),
        "status": status,
        "retry_safe": status in RETRYABLE_STATUS and (method in IDEMPOTENT_METHODS or "idempotency-key" in req),
        "retry_after": retry_after(resp.get("retry-after"), resp.get("date")),
        "cache": cache,
        "ttl": ttl,
        "keep_alive": keep_alive(version.upper(), resp),
    }
