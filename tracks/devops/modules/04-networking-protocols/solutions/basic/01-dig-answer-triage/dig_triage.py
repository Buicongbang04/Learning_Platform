import re

SECTION = re.compile(r"^;; (QUESTION|ANSWER|AUTHORITY|ADDITIONAL) SECTION:$")
HEADER = re.compile(r"->>HEADER<<-.*status: (\w+)")
FLAGS = re.compile(r"^;; flags:([^;]*);")
EDE = re.compile(r"^; EDE: (\d+)")


def split_sections(text: str) -> dict[str, list[str]]:
    """Trả {"QUESTION": [...], "ANSWER": [...], ...}: các dòng bản ghi của từng section, đã bỏ dòng trống."""
    sections: dict[str, list[str]] = {"QUESTION": [], "ANSWER": [], "AUTHORITY": [], "ADDITIONAL": []}
    current = None
    for line in text.splitlines():
        match = SECTION.match(line.strip())
        if match:
            current = match.group(1)
        elif not line.strip() or line.startswith(";;"):
            current = None if not line.strip() else current
        elif current:
            sections[current].append(line.strip())
    return sections


def norm(name: str) -> str:
    return name.lower().rstrip(".")


def parse_record(line: str) -> tuple[str, int, str, str]:
    """Một dòng bản ghi `name ttl class type rdata...` thành (name, ttl, type, rdata)."""
    name, ttl, _cls, rtype, *rdata = line.split()
    return norm(name), int(ttl), rtype.upper(), " ".join(rdata)


def in_bailiwick(name: str, zone: str) -> bool:
    return name == zone or name.endswith("." + zone)


def triage(text: str) -> dict:
    """Phân loại một output `dig`. Định dạng kết quả và quy tắc: xem README của bài."""
    status = HEADER.search(text).group(1)
    flags = next((m.group(1).split() for m in map(FLAGS.match, text.splitlines()) if m), [])
    ede = next((int(m.group(1)) for m in map(EDE.match, text.splitlines()) if m), None)
    sections = split_sections(text)
    qname_raw, *_rest, qtype = sections["QUESTION"][0].lstrip(";").split()
    qname = norm(qname_raw)
    answer = [parse_record(line) for line in sections["ANSWER"]]
    authority = [parse_record(line) for line in sections["AUTHORITY"]]
    additional = [parse_record(line) for line in sections["ADDITIONAL"]]

    chain = [qname]
    cnames = {name: norm(rdata) for name, _ttl, rtype, rdata in answer if rtype == "CNAME"}
    while chain[-1] in cnames and cnames[chain[-1]] not in chain:
        chain.append(cnames[chain[-1]])
    answers = sorted(rdata for _name, _ttl, rtype, rdata in answer if rtype == qtype.upper())
    soa = next(((ttl, rdata) for _name, ttl, rtype, rdata in authority if rtype == "SOA"), None)
    ns = [(name, norm(rdata)) for name, _ttl, rtype, rdata in authority if rtype == "NS"]

    kind = {"NXDOMAIN": "nxdomain", "SERVFAIL": "servfail", "REFUSED": "refused"}.get(status, "error")
    if status == "NOERROR":
        if answers:
            kind = "answer"
        elif soa is None and ns and "aa" not in flags:
            kind = "referral"
        else:
            kind = "nodata"

    ttl = None
    if kind == "answer":
        ttl = min(record[1] for record in answer)
    elif kind in ("nxdomain", "nodata") and soa is not None:
        ttl = min(soa[0], int(soa[1].split()[-1]))

    missing_glue: list[str] = []
    if kind == "referral":
        glued = {name for name, _ttl, rtype, _rdata in additional if rtype in ("A", "AAAA")}
        missing_glue = sorted({target for zone, target in ns if in_bailiwick(target, zone) and target not in glued})

    return {
        "qname": qname,
        "qtype": qtype.upper(),
        "status": status,
        "kind": kind,
        "authoritative": "aa" in flags,
        "cname_chain": chain,
        "answers": answers,
        "ttl": ttl,
        "missing_glue": missing_glue,
        "ede": ede,
    }
