"""ACL theo thư mục: `QUILLO_ACL="legal:legal/,finance:finance/"` cho nhóm `legal` xem tài liệu có đường dẫn bắt đầu bằng
`legal/`. Tiền tố luôn là thư mục (thêm `/` nếu thiếu). Tài liệu không khớp tiền tố nào chỉ admin thấy."""

import re

GROUP = re.compile(r"^[A-Za-z0-9._-]+$")
FOLDER = re.compile(r"^[A-Za-z0-9._ /-]+$")


def parse(spec: str) -> list[tuple[str, str]]:
    rules = []
    for item in (part.strip() for part in spec.split(",")):
        if not item:
            continue
        group, sep, prefix = item.partition(":")
        prefix = prefix.strip().strip("/")
        if not sep or not GROUP.match(group.strip()) or not prefix or not FOLDER.match(prefix) \
                or any(part in {"", ".", ".."} for part in prefix.split("/")):
            raise ValueError(f"QUILLO_ACL: '{item}' không đúng dạng nhóm:thư_mục (vd. legal:legal/)")
        rules.append((group.strip(), prefix + "/"))
    return rules


def prefixes(rules: list[tuple[str, str]], groups: set[str]) -> list[str]:
    """Các tiền tố đường dẫn mà người thuộc `groups` được xem."""
    return sorted({prefix for group, prefix in rules if group in groups})


def visible(path: str, allowed: list[str]) -> bool:
    return any(path.startswith(prefix) for prefix in allowed)
