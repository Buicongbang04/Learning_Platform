import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)

HEADINGS = ["Bối cảnh", "Kiến trúc", "Dịch vụ", "Chi phí", "Quyết định", "Bảo mật", "Vận hành"]

# Mỗi nhóm: các cách viết chấp nhận được (viết thường)
SERVICES = {
    "aws": {
        "compute": ["ec2", "ecs", "eks", "lambda", "fargate", "emr"],
        "object_storage": ["s3"],
        "managed_sql": ["rds", "aurora"],
        "etl": ["glue", "emr"],
        "warehouse": ["redshift", "athena"],
        "streaming": ["kinesis", "msk"],
    },
    "azure": {
        "compute": ["virtual machine", "aks", "container apps", "functions", "databricks"],
        "object_storage": ["blob", "adls", "data lake storage"],
        "managed_sql": ["sql database", "azure database for postgresql", "sql managed instance"],
        "etl": ["data factory", "databricks", "synapse pipelines", "fabric"],
        "warehouse": ["synapse", "fabric"],
        "streaming": ["event hubs", "stream analytics"],
    },
    "gcp": {
        "compute": ["compute engine", "gke", "cloud run", "dataproc", "cloud functions"],
        "object_storage": ["cloud storage", "gcs"],
        "managed_sql": ["cloud sql", "alloydb", "spanner"],
        "etl": ["dataflow", "dataproc", "data fusion"],
        "warehouse": ["bigquery"],
        "streaming": ["pub/sub", "pubsub"],
    },
}

KEYS = {"storage", "compute", "warehouse", "streaming", "egress", "other", "total"}


def design():
    return ex.read("design.md")


def est():
    return ex.module("estimate.py")


def section(text, keyword):
    parts = re.split(r"^## ", text, flags=re.M)
    for part in parts[1:]:
        if keyword.lower() in part.splitlines()[0].lower():
            return part
    return ""


def test_cloud_chosen():
    assert est().CLOUD in SERVICES, 'CLOUD phải là "aws", "azure" hoặc "gcp"'


def test_design_complete():
    text = design()
    assert "TODO" not in text, "Còn TODO trong design.md"
    for keyword in HEADINGS:
        assert section(text, keyword), f"Thiếu mục ## ... {keyword}"
    assert "```mermaid" in text, "Cần ít nhất một sơ đồ mermaid"
    adrs = re.findall(r"^### ADR-\d+", text, flags=re.M)
    assert len(adrs) >= 3, "Cần ít nhất 3 mục ### ADR-n"
    for word in ("Lựa chọn", "Lý do", "Đánh đổi"):
        assert section(text, "Quyết định").count(word) >= 3, f"Mỗi ADR cần phần {word}"


def test_services_of_chosen_cloud():
    cloud = est().CLOUD
    if cloud not in SERVICES:
        pytest.fail("Chưa chọn CLOUD")
    text = design().lower()
    covered = [cat for cat, names in SERVICES[cloud].items() if any(n in text for n in names)]
    assert len(covered) >= 5, f"Chỉ thấy dịch vụ {cloud} cho nhóm {covered}"


def test_security_section():
    sec = section(design(), "Bảo mật").lower()
    assert any(w in sec for w in ("iam role", "managed identity", "service account", "role")), "Nêu danh tính workload"
    assert any(w in sec for w in ("kms", "mã hoá", "encrypt", "key vault", "cmek")), "Nêu mã hoá"
    assert any(w in sec for w in ("vpc", "vnet", "private endpoint", "private link", "private service connect",
                                  "privatelink")), "Nêu mạng riêng"
    assert "pii" in sec


def test_estimate_shape_and_consistency():
    result = est().estimate()
    assert set(result) == KEYS
    assert all(v >= 0 for v in result.values())
    parts = sum(v for k, v in result.items() if k != "total")
    assert result["total"] == pytest.approx(parts, abs=0.05)


def test_estimate_monotonic():
    mod = est()
    base = mod.estimate()
    more_data = mod.estimate({**mod.DEFAULT_WORKLOAD, "raw_gb_per_day": mod.DEFAULT_WORKLOAD["raw_gb_per_day"] * 2})
    assert more_data["storage"] > base["storage"]
    more_queries = mod.estimate({**mod.DEFAULT_WORKLOAD, "queries_per_day": mod.DEFAULT_WORKLOAD["queries_per_day"] * 5})
    assert more_queries["warehouse"] >= base["warehouse"]


def test_estimate_plausible_and_documented():
    total = est().estimate()["total"]
    assert 20 <= total <= 5000, f"Tổng {total} USD/tháng không hợp lý cho quy mô Olist"
    cost_section = section(design(), "Chi phí")
    numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", cost_section)]
    assert any(abs(n - total) <= 0.1 * total for n in numbers), \
        f"Mục chi phí trong design.md cần ghi tổng ≈ {total:.0f} USD (kết quả estimate.py)"
