import re
from pathlib import Path

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
HEADROOM_MIB = 12288
OPTION_COLUMNS = ["phương án", "mtls", "traffic", "observability", "vận hành", "ram ước tính (mib)"]
COST_COLUMNS = ["thành phần", "số lượng", "mib mỗi cái", "tổng (mib)"]
TOOLS = {"linkerd": ("linkerd",), "istio": ("istio",), "consul": ("consul",), "cilium": ("cilium",), "envoy": ("envoy",)}
NO_MESH = re.compile(r"không (dùng )?mesh|no mesh|không có mesh", re.I)
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*-\s+(.+)$", text, re.M)]


def steps(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*\d+\.\s+(.+)$", text, re.M)]


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
    numbers = NUMBER.findall((cell or "").replace(" ", ""))
    return float(numbers[-1].replace(",", ".")) if numbers else None


def tools_in(text: str) -> set[str]:
    low = text.lower()
    return {name for name, words in TOOLS.items() if any(re.search(rf"\b{w}\b", low) for w in words)}


def doc_problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 9):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    context = section(doc, 1)
    if len(bullets(context)) < 4:
        found.append("Phần 1: ít nhất 4 gạch đầu dòng yêu cầu và ràng buộc")
    if "mtls" not in context.lower() or "pci" not in context.lower():
        found.append("Phần 1: nhắc lại yêu cầu mTLS và phạm vi PCI")
    header, options = table(section(doc, 2))
    if header[:len(OPTION_COLUMNS)] != OPTION_COLUMNS:
        found.append(f"Phần 2: bảng cần đúng các cột {OPTION_COLUMNS}")
        options = []
    elif len(options) < 4:
        found.append(f"Phần 2: cần ít nhất 4 phương án, có {len(options)}")
    names = [o.get("phương án", "") for o in options]
    if options and not any(NO_MESH.search(n) for n in names):
        found.append("Phần 2: phải có phương án không dùng mesh để so sánh")
    compared = set().union(*(tools_in(n) for n in names)) if names else set()
    if options and len(compared) < 2:
        found.append(f"Phần 2: so sánh ít nhất 2 công cụ trong Linkerd, Istio, Consul, Cilium, Envoy; đang có {sorted(compared)}")
    for option in options:
        if amount(option.get("ram ước tính (mib)", "")) is None:
            found.append(f"Phần 2: phương án {option.get('phương án')!r} thiếu RAM ước tính bằng số")
    decision = section(doc, 3)
    if len(bullets(decision)) < 3:
        found.append("Phần 3: ít nhất 3 gạch đầu dòng lý do")
    chosen = tools_in(decision) | ({"none"} if NO_MESH.search(decision) else set())
    if options and not chosen & (compared | {"none"}):
        found.append("Phần 3: quyết định phải chọn một phương án đã so sánh ở phần 2")
    cost = section(doc, 4)
    header, rows = table(cost)
    if header[:len(COST_COLUMNS)] != COST_COLUMNS:
        found.append(f"Phần 4: bảng cần đúng các cột {COST_COLUMNS}")
        rows = []
    if header and len(rows) < 3:
        found.append(f"Phần 4: cần ít nhất 3 thành phần, có {len(rows)}")
    values = []
    for row in rows:
        count, each, total = (amount(row.get(k, "")) for k in COST_COLUMNS[1:])
        if None in (count, each, total):
            found.append(f"Phần 4: dòng {row.get('thành phần')!r} cần số lượng, MiB mỗi cái và tổng bằng số")
            continue
        values.append(total)
        if abs(count * each - total) > max(1.0, 0.01 * total):
            found.append(f"Phần 4: dòng {row.get('thành phần')!r}: {count:g} x {each:g} khác {total:g}")
    claimed = re.search(r"^Tổng:\s*(\d+(?:[.,]\d+)?)\s*MiB", cost, re.M)
    if not claimed:
        found.append("Phần 4: thiếu dòng 'Tổng: <số> MiB'")
    else:
        total = float(claimed.group(1).replace(",", "."))
        if total > HEADROOM_MIB:
            found.append(f"Phần 4: tổng {total:g} MiB vượt phần RAM còn trống {HEADROOM_MIB} MiB")
        if values and abs(sum(values) - total) > max(1.0, 0.01 * total):
            found.append(f"Phần 4: cộng các dòng được {sum(values):g} MiB, khác dòng Tổng {total:g} MiB")
    rollout = section(doc, 5)
    if len(steps(rollout)) < 5:
        found.append("Phần 5: ít nhất 5 bước đánh số")
    if not re.search(r"rollback|quay lui|quay lại", rollout, re.I):
        found.append("Phần 5: mỗi kế hoạch rollout cần cách quay lui (rollback)")
    duties = flat(section(doc, 6))
    if len(bullets(section(doc, 6))) < 3 or "chứng chỉ" not in duties or "nâng cấp" not in duties:
        found.append("Phần 6: ít nhất 3 gạch đầu dòng, nói ai lo chứng chỉ (trust anchor, issuer) và nâng cấp mesh")
    risks = flat(section(doc, 7))
    if len(bullets(section(doc, 7))) < 3 or not any(w in risks for w in ("đường lui", "gỡ mesh", "gỡ bỏ")):
        found.append("Phần 7: ít nhất 3 gạch đầu dòng, nói tới đường lui khi mesh gây sự cố")
    if len(bullets(section(doc, 8))) < 2:
        found.append("Phần 8: ít nhất 2 điều kiện cần xem lại quyết định")
    return found


def test_decision_document():
    found = doc_problems(ex.read("DECISION.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = doc_problems((FIXTURES / "DECISION.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and any(f.startswith("Phần 2: cần ít nhất 4 phương án") for f in found), found


def test_checks_catch_weak_document():
    found = "\n".join(doc_problems((FIXTURES / "DECISION.weak.md").read_text(encoding="utf-8")))
    for needle in ("phương án không dùng mesh", "160 x 4 khác 600", "vượt phần RAM", "khác dòng Tổng", "cách quay lui", "Phần 6"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_document_passes():
    found = doc_problems((FIXTURES / "DECISION.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)
