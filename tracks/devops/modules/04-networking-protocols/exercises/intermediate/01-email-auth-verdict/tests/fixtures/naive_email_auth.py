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


def policy_with_fallthrough(domain: str, records: dict, suffixes: set[str]) -> str | None:
    found = [t for t in records.get((f"_dmarc.{domain}", "TXT"), []) if t.lower().startswith("v=dmarc1")]
    if len(found) == 1:
        return found[0].split("p=", 1)[1].split(";")[0].strip()
    org = last_two(domain) if not domain.endswith(".com.br") else ".".join(domain.split(".")[-3:])
    tags = dict(p.strip().split("=", 1) for p in records[(f"_dmarc.{org}", "TXT")][0].split(";"))
    return tags.get("sp", tags["p"])
