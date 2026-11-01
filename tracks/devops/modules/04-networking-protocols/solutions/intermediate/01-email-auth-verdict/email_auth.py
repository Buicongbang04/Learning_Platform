import ipaddress
from email import message_from_string
from email.utils import getaddresses, parseaddr
from pathlib import Path

import dns.rdatatype
import dns.zone

AUTHSERV_ID = "mx.cliente-mail.example"
LOOKUP_LIMIT = 10
LOWER = {"reject": "quarantine", "quarantine": "deliver", "none": "deliver"}
DISPOSITION = {"reject": "reject", "quarantine": "quarantine", "none": "deliver"}


def load_records(zone_dir: Path) -> dict[tuple[str, str], list[str]]:
    """Đọc mọi `<tên miền>.zone` thành {(tên chữ thường không dấu chấm cuối, loại): [rdata, ...]}; TXT đã ghép chuỗi."""
    records: dict[tuple[str, str], list[str]] = {}
    for path in sorted(Path(zone_dir).glob("*.zone")):
        zone = dns.zone.from_file(str(path), origin=path.stem, relativize=False)
        for name, rdataset in zone.iterate_rdatasets():
            key = (name.to_text().rstrip(".").lower(), dns.rdatatype.to_text(rdataset.rdtype))
            for rdata in rdataset:
                text = b"".join(rdata.strings).decode() if key[1] == "TXT" else rdata.to_text()
                records.setdefault(key, []).append(text)
    return records


def load_suffixes(path: Path) -> set[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return {line.strip().lower() for line in lines if line.strip() and not line.startswith("#")}


def norm(domain: str) -> str:
    return domain.strip().rstrip(".").lower()


def org_domain(domain: str, suffixes: set[str]) -> str:
    domain = norm(domain)
    labels = domain.split(".")
    matches = [s for s in suffixes if domain == s or domain.endswith("." + s)]
    suffix = max(matches, key=lambda s: s.count("."), default=labels[-1])
    if domain == suffix:
        return domain
    keep = suffix.count(".") + 2
    return ".".join(labels[-keep:])


def aligned(a: str, b: str, mode: str, suffixes: set[str]) -> bool:
    if mode == "s":
        return norm(a) == norm(b)
    return org_domain(a, suffixes) == org_domain(b, suffixes)


class PermError(Exception):
    pass


def spf_record(domain: str, records: dict) -> str | None:
    found = [t for t in records.get((norm(domain), "TXT"), []) if t.lower() == "v=spf1" or t.lower().startswith("v=spf1 ")]
    if len(found) > 1:
        raise PermError(f"{domain}: nhiều bản ghi SPF")
    return found[0] if found else None


def split_target(arg: str, default_domain: str) -> tuple[str, int | None]:
    domain, _, prefix = arg.partition("/")
    return (norm(domain) if domain else default_domain), (int(prefix) if prefix else None)


def ip_in_hosts(ip, hosts: list[str], prefix: int | None) -> bool:
    for host in hosts:
        address = ipaddress.ip_address(host)
        if address.version != ip.version:
            continue
        bits = prefix if (prefix is not None and ip.version == 4) else address.max_prefixlen
        if ip in ipaddress.ip_network(f"{address}/{bits}", strict=False):
            return True
    return False


def addresses(name: str, records: dict) -> list[str]:
    return records.get((name, "A"), []) + records.get((name, "AAAA"), [])


def evaluate_spf(ip, domain: str, records: dict, counter: list[int]) -> str:
    record = spf_record(domain, records)
    if record is None:
        return "none"
    redirect = None
    for term in record.split()[1:]:
        lowered = term.lower()
        if lowered.startswith("redirect="):
            redirect = norm(term.split("=", 1)[1])
            continue
        if "=" in lowered.split(":", 1)[0]:
            continue
        qualifier = term[0] if term[0] in "+-~?" else "+"
        mechanism = term[1:] if term[0] in "+-~?" else term
        name, _, arg = mechanism.partition(":")
        name = name.lower()
        if "/" in name:
            name, _, cidr = name.partition("/")
            arg = f"{arg}/{cidr}"
        if name in ("include", "a", "mx"):
            counter[0] += 1
            if counter[0] > LOOKUP_LIMIT:
                raise PermError("quá 10 lần tra DNS")
        if name == "all":
            matched = True
        elif name in ("ip4", "ip6"):
            network = ipaddress.ip_network(arg, strict=False)
            matched = network.version == ip.version and ip in network
        elif name == "a":
            target, prefix = split_target(arg, domain)
            matched = ip_in_hosts(ip, addresses(target, records), prefix)
        elif name == "mx":
            target, prefix = split_target(arg, domain)
            exchanges = [norm(mx.split()[-1]) for mx in records.get((target, "MX"), [])]
            matched = any(ip_in_hosts(ip, addresses(host, records), prefix) for host in exchanges)
        elif name == "include":
            result = evaluate_spf(ip, norm(arg), records, counter)
            if result == "none":
                raise PermError(f"include:{arg} không có SPF")
            matched = result == "pass"
        else:
            raise PermError(f"cơ chế không hỗ trợ: {term}")
        if matched:
            return {"+": "pass", "-": "fail", "~": "softfail", "?": "neutral"}[qualifier]
    if redirect:
        counter[0] += 1
        if counter[0] > LOOKUP_LIMIT:
            raise PermError("quá 10 lần tra DNS")
        result = evaluate_spf(ip, redirect, records, counter)
        if result == "none":
            raise PermError(f"redirect={redirect} không có SPF")
        return result
    return "neutral"


def spf_check(ip: str, domain: str, records: dict) -> str:
    try:
        return evaluate_spf(ipaddress.ip_address(ip), norm(domain), records, [0])
    except PermError:
        return "permerror"


def dmarc_tags(text: str) -> dict[str, str]:
    tags = {}
    for part in text.split(";"):
        key, sep, value = part.strip().partition("=")
        if sep:
            tags[key.strip().lower()] = value.strip()
    return tags


def dmarc_records(domain: str, records: dict) -> list[dict[str, str]]:
    return [dmarc_tags(t) for t in records.get((f"_dmarc.{domain}", "TXT"), []) if t.strip().lower().startswith("v=dmarc1")]


def first_received(msg) -> tuple[str, str]:
    received = " ".join(msg.get_all("Received", [])[0].split())
    helo = received.split()[1]
    ip = received.split("[", 1)[1].split("]", 1)[0]
    return norm(helo), ip


def trusted_dkim_domains(msg) -> list[str]:
    results = msg.get_all("Authentication-Results", [])
    if not results:
        return []
    parts = [" ".join(p.split()) for p in results[0].split(";")]
    if norm(parts[0]) != AUTHSERV_ID:
        return []
    domains = []
    for part in parts[1:]:
        tokens = part.split()
        if tokens and tokens[0].lower() == "dkim=pass":
            domains += [norm(t.split("=", 1)[1]) for t in tokens if t.lower().startswith("header.d=")]
    return domains


def evaluate(raw: str, records: dict, suffixes: set[str]) -> dict:
    msg = message_from_string(raw)
    from_domain = norm(getaddresses(msg.get_all("From", []))[0][1].rsplit("@", 1)[1])
    helo, ip = first_received(msg)
    return_path = parseaddr(msg.get("Return-Path", ""))[1]
    spf_domain = norm(return_path.rsplit("@", 1)[1]) if "@" in return_path else helo
    spf = spf_check(ip, spf_domain, records)

    record, policy = None, None
    found = dmarc_records(from_domain, records)
    if len(found) == 1:
        record = found[0]
        policy = record.get("p", "none").lower()
    elif not found:
        org = org_domain(from_domain, suffixes)
        if org != from_domain:
            found = dmarc_records(org, records)
            if len(found) == 1:
                record = found[0]
                policy = record.get("sp", record.get("p", "none")).lower()
    tags = record or {}
    spf_ok = spf == "pass" and aligned(spf_domain, from_domain, tags.get("aspf", "r").lower(), suffixes)
    dkim_ok = any(aligned(d, from_domain, tags.get("adkim", "r").lower(), suffixes) for d in trusted_dkim_domains(msg))

    if record is None:
        dmarc = "none"
    else:
        dmarc = "pass" if spf_ok or dkim_ok else "fail"
    disposition = DISPOSITION[policy] if dmarc == "fail" else "deliver"
    pct = int(tags.get("pct", "100"))
    fallback = LOWER[policy] if dmarc == "fail" and pct < 100 else disposition
    return {
        "from_domain": from_domain,
        "spf_domain": spf_domain,
        "spf": spf,
        "spf_aligned": spf_ok,
        "dkim_aligned": dkim_ok,
        "dmarc": dmarc,
        "policy": policy,
        "disposition": disposition,
        "fallback": fallback,
    }
