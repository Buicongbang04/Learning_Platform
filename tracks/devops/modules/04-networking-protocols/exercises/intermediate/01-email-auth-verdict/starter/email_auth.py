import ipaddress
from email import message_from_string
from email.utils import getaddresses, parseaddr
from pathlib import Path

import dns.rdatatype
import dns.zone

AUTHSERV_ID = "mx.cliente-mail.example"
LOOKUP_LIMIT = 10


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


def org_domain(domain: str, suffixes: set[str]) -> str:
    """Organizational domain: hậu tố công khai dài nhất khớp + một nhãn bên trái (xem README)."""
    # TODO
    raise NotImplementedError


def aligned(a: str, b: str, mode: str, suffixes: set[str]) -> bool:
    """mode "s": hai tên bằng nhau; mode "r": cùng organizational domain. Không phân biệt hoa thường, bỏ dấu chấm cuối."""
    # TODO
    raise NotImplementedError


def spf_check(ip: str, domain: str, records: dict) -> str:
    """Kết quả SPF: pass, fail, softfail, neutral, none hoặc permerror (xem bảng quy tắc trong README)."""
    # TODO: tìm đúng một bản ghi v=spf1, duyệt cơ chế từ trái sang phải, đếm lượt tra DNS, xử lý include và redirect
    raise NotImplementedError


def evaluate(raw: str, records: dict, suffixes: set[str]) -> dict:
    """Kết luận cho một thư: 9 khoá from_domain, spf_domain, spf, spf_aligned, dkim_aligned, dmarc, policy,
    disposition, fallback (xem README)."""
    # TODO: From, header Received trên cùng (HELO, IP), Return-Path, Authentication-Results trên cùng
    # TODO: tìm bản ghi DMARC (tên miền From, rồi organizational domain với sp), alignment, disposition và pct
    raise NotImplementedError
