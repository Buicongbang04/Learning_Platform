import re

SECTION = re.compile(r"^;; (QUESTION|ANSWER|AUTHORITY|ADDITIONAL) SECTION:$")


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


def parse_record(line: str) -> tuple[str, int, str, str]:
    """Một dòng bản ghi `name ttl class type rdata...` thành (name, ttl, type, rdata)."""
    # TODO: tách theo khoảng trắng; name chữ thường, bỏ dấu chấm cuối; rdata gộp khoảng trắng thành một dấu cách
    raise NotImplementedError


def triage(text: str) -> dict:
    """Phân loại một output `dig`. Định dạng kết quả và quy tắc: xem README của bài."""
    # TODO: đọc dòng ->>HEADER<<- (status), dòng flags (aa), dòng EDE nếu có, câu hỏi trong QUESTION SECTION
    # TODO: đi theo chuỗi CNAME trong ANSWER, lấy answers, tính ttl theo kind
    # TODO: với referral, tìm NS trong bailiwick không có glue A/AAAA trong ADDITIONAL
    raise NotImplementedError
