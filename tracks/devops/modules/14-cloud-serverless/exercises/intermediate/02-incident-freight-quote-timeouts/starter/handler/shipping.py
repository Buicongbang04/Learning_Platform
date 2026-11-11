import json
import os
import urllib.error
import urllib.request

QUOTE_URL = os.environ["QUOTE_URL"]

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class QuoteError(RuntimeError):
    pass


def quote(order_id: str, timeout: float = 5.0) -> int:
    """Hỏi giá vận chuyển của một đơn; trả freight_cents. Lỗi HTTP, quá giờ hay body sai đều ném QuoteError."""
    url = f"{QUOTE_URL}/quote?order_id={urllib.request.quote(order_id)}"
    try:
        with _opener.open(url, timeout=timeout) as response:
            return int(json.load(response)["freight_cents"])
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        raise QuoteError(f"{order_id}: {error}") from error
