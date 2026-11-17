import re
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
WORKLOADS = {"deployment", "statefulset", "daemonset", "job", "cronjob", "pod tĩnh", "không chạy trong cluster"}
SERVICES = {"clusterip", "headless", "nodeport", "loadbalancer", "externalname", "không"}
OLIST = {
    "api": None,
    "worker": None,
    "postgres": {"statefulset", "không chạy trong cluster"},
    "redis": None,
    "fluent-bit": {"daemonset"},
    "report": {"cronjob"},
    "migration": {"job"},
    "thumbnail": {"job"},
    "payment": None,
}
OLIST_SERVICES = {"payment": {"externalname"}}
KEYWORDS = {
    3: (("ingress", "gateway"), ("service",)),
    4: (("maxunavailable", "maxsurge"), ("partition", "ondelete", "podmanagementpolicy"), ("poddisruptionbudget", "pdb")),
    5: (("storageclass",), ("readwriteonce", "rwo"), ("retain", "reclaim"), ("backup", "snapshot", "pg_dump")),
}
MIN_BULLETS = {4: 4, 5: 3, 6: 4}


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[cell.strip() for cell in row] for row in rows[2:]]


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```"))).strip()


def decision_problems(doc: str, components: dict, services: dict) -> list[str]:
    rows = [r for r in table_rows(section(doc, 2)) if len(r) >= 6]
    found = []
    for key, expected in components.items():
        row = next((r for r in rows if key in r[0].lower()), None)
        if row is None:
            found.append(f"Phần 2: thiếu dòng cho {key}")
            continue
        workload, service, reason = row[1].strip("* ").lower(), row[2].strip("* ").lower(), row[5]
        if workload not in WORKLOADS:
            found.append(f"Phần 2: cột Workload của {key} phải là một trong {sorted(WORKLOADS)}, đang là '{row[1]}'")
        elif expected and workload not in expected:
            found.append(f"Phần 2: {key} chọn '{row[1]}' chưa đúng loại workload")
        if service not in SERVICES:
            found.append(f"Phần 2: cột Service của {key} phải là một trong {sorted(SERVICES)}, đang là '{row[2]}'")
        elif key in services and service not in services[key]:
            found.append(f"Phần 2: Service của {key} chưa đúng loại")
        if "hostpath" in row[3].lower():
            found.append(f"Phần 2: {key} dùng hostPath, gắn dữ liệu vào một node và mở đường vào node")
        if len(reason) < 25 or "TODO" in reason:
            found.append(f"Phần 2: lý do cho {key} cần ít nhất 25 ký tự")
    return found


def problems(doc: str, components: dict = OLIST, services: dict = OLIST_SERVICES) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 7):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    found += decision_problems(doc, components, services)
    if "```mermaid" not in section(doc, 3):
        found.append("Phần 3: cần một khối mermaid")
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = section(doc, number).lower()
        for group in groups:
            if not any(word in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


RIDE = {"dispatch": None, "tracking": {"statefulset"}, "node-agent": {"daemonset"}, "settlement": {"cronjob"},
        "reindex": {"job"}, "maps": None}


def test_design_document():
    found = problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = problems((FIXTURES / "DESIGN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and "Phần 3: cần một khối mermaid" in found
    assert any(p.startswith("Phần 2: thiếu dòng cho") for p in found)


def test_checks_catch_weak_design():
    found = "\n".join(problems((FIXTURES / "DESIGN.weak.md").read_text(encoding="utf-8")))
    for needle in ("fluent-bit chọn 'Deployment'", "report chọn 'Deployment'", "Service của payment", "thiếu dòng cho thumbnail",
                   "chưa nói tới partition", "chưa nói tới retain", "lý do cho redis", "dùng hostPath"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_design_passes():
    found = problems((FIXTURES / "DESIGN.good.md").read_text(encoding="utf-8"), RIDE, {"maps": {"externalname"}})
    assert not found, "\n".join(found)


@pytest.mark.parametrize("cell,ok", [("Deployment", True), ("**StatefulSet**", True), ("Không chạy trong cluster", True),
                                     ("ReplicaSet", False), ("Pod", False)])
def test_workload_values(cell, ok):
    doc = "## 2. Bảng\n\n| Thành phần | Workload | Service | Storage | Probe | Lý do |\n| --- | --- | --- | --- | --- | --- |\n"
    doc += f"| api | {cell} | ClusterIP | Không | readiness | lý do đủ dài để vượt qua ngưỡng tối thiểu |\n"
    assert (not decision_problems(doc, {"api": None}, {})) is ok
