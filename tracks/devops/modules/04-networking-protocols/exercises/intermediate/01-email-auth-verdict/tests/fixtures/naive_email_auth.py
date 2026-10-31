from email import message_from_string
from email.utils import parseaddr


def last_two(domain: str) -> str:
    return ".".join(domain.lower().rstrip(".").split(".")[-2:])


def aligned(a: str, b: str, mode: str, suffixes: set[str]) -> bool:
    return a.lower() == b.lower() if mode == "s" else last_two(a) == last_two(b)


def evaluate(raw: str, records: dict, suffixes: set[str]) -> dict:
    msg = message_from_string(raw)
    from_domain = parseaddr(msg["From"])[1].rsplit("@", 1)[1].lower()
    passed = any(
        f"header.d={from_domain}" in " ".join(h.split()) and "dkim=pass" in h
        for h in msg.get_all("Authentication-Results", [])
    )
    return {"from_domain": from_domain, "dmarc": "pass" if passed else "fail"}
