import re
from pathlib import Path

import dns.exception
import dns.rdatatype
import dns.zone

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
ORIGIN = "olistmarket.com.br."
CNAME_CONFLICT = "Zone: có tên vừa CNAME vừa bản ghi khác, hoặc CNAME ở apex"
LOOKUP = re.compile(r"^[+\-~?]?(include:|a$|a:|a/|mx$|mx:|mx/|exists:|ptr|redirect=)", re.I)


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def zone_block(doc: str) -> str | None:
    match = re.search(r"```zone\n(.*?)```", section(doc, 2), re.S)
    return match.group(1) if match else None


def txts(zone, name: str) -> list[str]:
    node = zone.get_node(name)
    rdataset = node.get_rdataset(1, dns.rdatatype.TXT) if node else None
    return [b"".join(r.strings).decode() for r in rdataset] if rdataset else []


def zone_problems(text: str) -> list[str]:
    try:
        zone = dns.zone.from_text(text, origin=ORIGIN, relativize=False, check_origin=False)
    except dns.exception.DNSException as exc:
        if exc.__class__.__name__ == "CNAMEAndOtherData":
            return [CNAME_CONFLICT]
        return [f"Zone: không đọc được ({exc.__class__.__name__}: {exc})"]
    found = []
    apex = zone.get_node(ORIGIN)
    if apex is None or apex.get_rdataset(1, dns.rdatatype.MX) is None:
        found.append("Zone: apex cần bản ghi MX")
    for name, node in zone.nodes.items():
        types = {r.rdtype for r in node.rdatasets}
        if dns.rdatatype.CNAME in types and (len(types) > 1 or name.to_text() == ORIGIN):
            found.append(CNAME_CONFLICT)
    spf = [t for t in txts(zone, ORIGIN) if t.lower().startswith("v=spf1")]
    if len(spf) != 1:
        found.append(f"Zone: apex cần đúng một bản ghi SPF, đang có {len(spf)}")
    else:
        terms = spf[0].split()[1:]
        if not terms or terms[-1].lower() not in ("-all", "~all"):
            found.append("Zone: SPF apex phải kết thúc bằng -all hoặc ~all")
        if sum(1 for t in terms if LOOKUP.match(t)) > 10:
            found.append("Zone: SPF apex quá 10 term cần tra DNS")
    subdomain_spf = [
        name for name in zone.nodes
        if name.to_text() != ORIGIN and not name.to_text().startswith("_")
        and any(t.lower().startswith("v=spf1") for t in txts(zone, name.to_text()))
    ]
    if not subdomain_spf:
        found.append("Zone: cần ít nhất một tên miền con (không bắt đầu bằng _) có SPF riêng cho envelope sender của ESP")
    dkim = []
    for name, node in zone.nodes.items():
        if "._domainkey." not in name.to_text():
            continue
        if node.get_rdataset(1, dns.rdatatype.CNAME) is not None:
            dkim.append(name)
        elif any(re.search(r"(^|;)\s*p=[A-Za-z0-9+/=]{20,}", t) and "v=DKIM1" in t for t in txts(zone, name.to_text())):
            dkim.append(name)
    if len(dkim) < 2:
        found.append("Zone: cần ít nhất 2 selector DKIM (TXT v=DKIM1 có p= không rỗng, hoặc CNAME tới nhà cung cấp)")
    dmarc = [t for t in txts(zone, "_dmarc." + ORIGIN) if t.lower().startswith("v=dmarc1")]
    if len(dmarc) != 1:
        found.append("Zone: cần đúng một bản ghi _dmarc v=DMARC1")
    else:
        tags = {k.strip().lower(): v.strip() for k, _, v in (p.partition("=") for p in dmarc[0].split(";"))}
        if tags.get("p", "").lower() != "none":
            found.append("Zone: _dmarc trong zone là giai đoạn đầu, phải p=none")
        if not tags.get("rua", "").startswith("mailto:"):
            found.append("Zone: _dmarc cần rua=mailto:...")
    if not any(t.startswith("v=STSv1") and "id=" in t for t in txts(zone, "_mta-sts." + ORIGIN)):
        found.append("Zone: cần _mta-sts TXT v=STSv1; id=...")
    if not any(t.startswith("v=TLSRPTv1") and "rua=" in t for t in txts(zone, "_smtp._tls." + ORIGIN)):
        found.append("Zone: cần _smtp._tls TXT v=TLSRPTv1; rua=...")
    return found


def problems(doc: str) -> list[str]:
    found = []
    if "TODO" in doc:
        found.append("Còn TODO")
    senders = [r for r in table_rows(section(doc, 1)) if len(r) >= 5 and all(r[:5])]
    if len(senders) < 4:
        found.append("Phần 1: ít nhất 4 nguồn gửi, đủ 5 cột")
    block = zone_block(doc)
    if block is None:
        found.append("Phần 2: cần một khối ```zone")
    else:
        found += zone_problems(block)
    phases = [r for r in table_rows(section(doc, 3)) if len(r) >= 4 and all(r[:4])]
    policies = [m.group(1).lower() for r in phases for m in [re.search(r"\bp=(none|quarantine|reject)\b", r[1], re.I)] if m]
    if len(phases) < 3:
        found.append("Phần 3: ít nhất 3 giai đoạn, đủ 4 cột")
    first = {p: policies.index(p) for p in ("none", "quarantine", "reject") if p in policies}
    if list(first) != ["none", "quarantine", "reject"] or sorted(first.values()) != list(first.values()):
        found.append("Phần 3: lộ trình phải đi qua p=none, p=quarantine, p=reject theo thứ tự")
    for number, label, minimum in ((4, "giám sát", 3), (5, "rủi ro", 3), (6, "biện pháp khác", 3)):
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng ({label})")
    return found


def test_plan_document():
    found = problems(ex.read("PLAN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "PLAN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found
    assert "Zone: apex cần bản ghi MX" in found
    assert any(p.startswith("Phần 3: lộ trình") for p in found)


def test_checks_catch_bad_zone():
    found = zone_problems((FIXTURES / "bad.zone").read_text(encoding="utf-8"))
    assert zone_problems((FIXTURES / "bad-cname.zone").read_text(encoding="utf-8")) == [CNAME_CONFLICT]
    assert CNAME_CONFLICT in zone_problems(f"$ORIGIN {ORIGIN}\n@ 300 IN CNAME lb.example.net.\n")
    for expected in (
        "Zone: apex cần bản ghi MX",
        "Zone: apex cần đúng một bản ghi SPF, đang có 2",
        "Zone: cần ít nhất 2 selector DKIM (TXT v=DKIM1 có p= không rỗng, hoặc CNAME tới nhà cung cấp)",
        "Zone: _dmarc trong zone là giai đoạn đầu, phải p=none",
        "Zone: _dmarc cần rua=mailto:...",
        "Zone: cần _mta-sts TXT v=STSv1; id=...",
    ):
        assert expected in found, f"Phép kiểm phải bắt '{expected}'. Bắt được: {found}"
    one_spf = (FIXTURES / "bad.zone").read_text(encoding="utf-8").replace('@                    IN TXT    "v=spf1 include:_spf.google.com -all"\n', "")
    assert "Zone: SPF apex quá 10 term cần tra DNS" in zone_problems(one_spf)
