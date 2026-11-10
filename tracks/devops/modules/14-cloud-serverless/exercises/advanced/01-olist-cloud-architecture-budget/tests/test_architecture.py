import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
BUDGET = 300
PROVIDERS = {
    "aws": ("aws", "amazon"), "azure": ("azure",), "gcp": ("gcp", "google cloud"), "digitalocean": ("digitalocean",),
    "alibaba": ("alibaba",), "hetzner": ("hetzner",), "contabo": ("contabo",), "heroku": ("heroku",),
    "cloudflare": ("cloudflare",), "vercel": ("vercel",), "netlify": ("netlify",),
}
OPTION_COLUMNS = ["phương án", "nhà cung cấp", "chi phí/tháng (usd)", "vận hành", "rủi ro"]
COST_COLUMNS = ["hạng mục", "đơn giá", "lượng", "thành tiền (usd)"]
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def flat(text: str) -> str:
    return " ".join(text.lower().split())


def table(text: str) -> tuple[list[str], list[dict]]:
    lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return [], []
    split = [[cell.strip().strip("`").strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    header = [cell.lower() for cell in split[0]]
    return header, [dict(zip(header, row)) for row in split[2:]]


def amount(cell: str) -> float | None:
    numbers = NUMBER.findall(cell or "")
    return float(numbers[-1].replace(",", ".")) if numbers else None


def providers_in(text: str) -> set[str]:
    low = text.lower()
    return {name for name, words in PROVIDERS.items() if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)}


def doc_problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 9):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    context = section(doc, 1)
    if len(bullets(context)) < 4:
        found.append("Phần 1: ít nhất 4 gạch đầu dòng ràng buộc")
    if str(BUDGET) not in context or not re.search(r"\bRPO\b|\bRTO\b", context):
        found.append(f"Phần 1: nhắc lại ngân sách {BUDGET} USD và RPO/RTO")
    header, options = table(section(doc, 2))
    if header[:len(OPTION_COLUMNS)] != OPTION_COLUMNS:
        found.append(f"Phần 2: bảng cần đúng các cột {OPTION_COLUMNS}")
        options = []
    elif len(options) < 3:
        found.append(f"Phần 2: cần ít nhất 3 phương án, có {len(options)}")
    compared = set().union(*(providers_in(o.get("nhà cung cấp", "")) for o in options)) if options else set()
    if options and len(compared) < 3:
        found.append(f"Phần 2: so sánh ít nhất 3 nhà cung cấp khác nhau, đang có {sorted(compared)}")
    for option in options:
        if amount(option.get("chi phí/tháng (usd)", "")) is None:
            found.append(f"Phần 2: phương án {option.get('phương án')!r} thiếu chi phí bằng số")
    decision = section(doc, 3)
    if len(bullets(decision)) < 3:
        found.append("Phần 3: ít nhất 3 gạch đầu dòng lý do")
    if compared and not providers_in(decision) & compared:
        found.append("Phần 3: quyết định phải chọn một nhà cung cấp đã so sánh ở phần 2")
    if "region" not in decision.lower():
        found.append("Phần 3: nói rõ region và vì sao")
    if "```mermaid" not in section(doc, 4):
        found.append("Phần 4: cần sơ đồ mermaid")
    cost = section(doc, 5)
    header, rows = table(cost)
    if header[:len(COST_COLUMNS)] != COST_COLUMNS:
        found.append(f"Phần 5: bảng cần đúng các cột {COST_COLUMNS}")
        rows = []
    items = [r for r in rows if not r.get("hạng mục", "").lower().startswith("tổng")]
    if header and len(items) < 5:
        found.append(f"Phần 5: cần ít nhất 5 hạng mục chi phí, có {len(items)}")
    values = [amount(r.get("thành tiền (usd)", "")) for r in items]
    if any(v is None for v in values):
        found.append("Phần 5: mỗi hạng mục cần thành tiền bằng số")
    total = re.search(r"^.*Tổng.*?(\d+(?:[.,]\d+)?)\s*USD", cost, re.M)
    if not total:
        found.append("Phần 5: thiếu dòng 'Tổng ... <số> USD'")
    else:
        claimed = float(total.group(1).replace(",", "."))
        if claimed > BUDGET:
            found.append(f"Phần 5: tổng {claimed} USD vượt ngân sách {BUDGET} USD")
        if items and all(v is not None for v in values) and abs(sum(values) - claimed) > max(1.0, 0.02 * claimed):
            found.append(f"Phần 5: cộng các hạng mục được {sum(values):.2f} USD, khác dòng Tổng {claimed} USD")
    if items and not any(re.search(r"egress|truyền dữ liệu ra|data transfer", r.get("hạng mục", ""), re.I) for r in items):
        found.append("Phần 5: thiếu hạng mục egress (dữ liệu ra Internet), khoản hay bị quên")
    shared = section(doc, 6)
    if len(bullets(shared)) < 3 or "nhà cung cấp" not in flat(shared):
        found.append("Phần 6: ít nhất 3 gạch đầu dòng, nói rõ phần của nhà cung cấp và phần của team")
    risks = flat(section(doc, 7))
    if len(bullets(section(doc, 7))) < 3 or "lock-in" not in risks or not any(w in risks for w in ("đường lui", "exit", "chuyển đi")):
        found.append("Phần 7: ít nhất 3 gạch đầu dòng, nói tới lock-in và đường lui")
    if len(bullets(section(doc, 8))) < 2:
        found.append("Phần 8: ít nhất 2 điều kiện cần xem lại quyết định")
    return found


def test_architecture_document():
    found = doc_problems(ex.read("ARCHITECTURE.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = doc_problems((FIXTURES / "ARCHITECTURE.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and any(f.startswith("Phần 2: cần ít nhất 3 phương án") for f in found)


def test_checks_catch_weak_document():
    found = "\n".join(doc_problems((FIXTURES / "ARCHITECTURE.weak.md").read_text(encoding="utf-8")))
    for needle in ("so sánh ít nhất 3 nhà cung cấp", "vượt ngân sách", "khác dòng Tổng", "thiếu hạng mục egress", "Phần 4: cần sơ đồ",
                   "Phần 7"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_document_passes():
    found = doc_problems((FIXTURES / "ARCHITECTURE.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)
