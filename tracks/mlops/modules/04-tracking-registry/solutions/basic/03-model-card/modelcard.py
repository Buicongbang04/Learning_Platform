import re

REQUIRED_HEADINGS = [
    "## Mục đích sử dụng",
    "## Dữ liệu huấn luyện",
    "## Hiệu năng",
    "## Hạn chế và rủi ro",
    "## Lineage",
]


def worst_slices(slices: dict, overall_mae: float, k: int = 3, min_n: int = 100) -> list[tuple[str, float]]:
    rows = [(name, s["mae"] / overall_mae) for name, s in slices.items() if s["n"] >= min_n]
    return sorted(rows, key=lambda row: (-row[1], row[0]))[:k]


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def build_model_card(info: dict) -> str:
    if not info.get("limitations"):
        raise ValueError("model card cần ít nhất một hạn chế")
    data, metrics, lineage = info["training_data"], info["metrics"], info["lineage"]
    ranked = worst_slices(info["slices"], metrics["mae"], k=len(info["slices"]), min_n=0)
    table = "\n".join(
        f"| {name} | {info['slices'][name]['n']} | {info['slices'][name]['mae']:.1f} | {ratio:.2f}x |"
        for name, ratio in ranked)
    return f"""# Model card: {info['name']} v{info['version']}

Người chịu trách nhiệm: {info['owner']}

{REQUIRED_HEADINGS[0]}

{info['intended_use']}

Ngoài phạm vi:

{_bullets(info.get('out_of_scope') or ['không có'])}

{REQUIRED_HEADINGS[1]}

- Phiên bản dữ liệu: `{data['data_version']}`
- Số dòng: {data['rows']}
- Giai đoạn: {data['period']}

{REQUIRED_HEADINGS[2]}

MAE tổng: {metrics['mae']:.1f} giây. Latency p95: {metrics['latency_p95_ms']:.1f} ms.

| Slice | n | MAE (giây) | So với MAE tổng |
| --- | --- | --- | --- |
{table}

{REQUIRED_HEADINGS[3]}

{_bullets(info['limitations'])}

{REQUIRED_HEADINGS[4]}

- run_id: `{lineage['run_id']}`
- git_commit: `{lineage['git_commit']}`
"""


def card_problems(text: str) -> list[str]:
    problems = [f"thiếu heading '{h}'" for h in REQUIRED_HEADINGS if not re.search(rf"^{re.escape(h)}\s*$", text, re.M)]
    if "TODO" in text:
        problems.append("còn TODO")

    def section(heading: str) -> str:
        match = re.search(rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        return match.group(1) if match else ""

    if not re.search(r"^\s*[-*] \S", section(REQUIRED_HEADINGS[3]), re.M):
        problems.append("phần Hạn chế và rủi ro không có gạch đầu dòng")
    if not re.search(r"^\|.*\|\s*\n\|[\s:|-]+\|", section(REQUIRED_HEADINGS[2]), re.M):
        problems.append("phần Hiệu năng không có bảng")
    if not re.search(r"\b[0-9a-f]{40}\b", section(REQUIRED_HEADINGS[4])):
        problems.append("phần Lineage thiếu git_commit 40 ký tự")
    return problems
