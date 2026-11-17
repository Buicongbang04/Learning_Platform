import json
import re
from pathlib import Path

import pytest
import yaml

from testkit import Exercise, KubeLab, kube_manifest_problems

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
PLACEHOLDER = "lab.olist.test"
REMOVED = {
    ("extensions/v1beta1", "Ingress"): "1.22", ("extensions/v1beta1", "Deployment"): "1.16",
    ("extensions/v1beta1", "DaemonSet"): "1.16", ("extensions/v1beta1", "NetworkPolicy"): "1.16",
    ("apps/v1beta1", "Deployment"): "1.16", ("apps/v1beta2", "Deployment"): "1.16",
    ("networking.k8s.io/v1beta1", "Ingress"): "1.22", ("networking.k8s.io/v1beta1", "IngressClass"): "1.22",
    ("rbac.authorization.k8s.io/v1beta1", "Role"): "1.22", ("rbac.authorization.k8s.io/v1beta1", "ClusterRole"): "1.22",
    ("rbac.authorization.k8s.io/v1beta1", "RoleBinding"): "1.22",
    ("rbac.authorization.k8s.io/v1beta1", "ClusterRoleBinding"): "1.22",
    ("apiextensions.k8s.io/v1beta1", "CustomResourceDefinition"): "1.22",
    ("scheduling.k8s.io/v1beta1", "PriorityClass"): "1.22", ("coordination.k8s.io/v1beta1", "Lease"): "1.22",
    ("batch/v1beta1", "CronJob"): "1.25", ("policy/v1beta1", "PodDisruptionBudget"): "1.25",
    ("policy/v1beta1", "PodSecurityPolicy"): "1.25", ("discovery.k8s.io/v1beta1", "EndpointSlice"): "1.25",
    ("autoscaling/v2beta1", "HorizontalPodAutoscaler"): "1.25", ("node.k8s.io/v1beta1", "RuntimeClass"): "1.25",
    ("autoscaling/v2beta2", "HorizontalPodAutoscaler"): "1.26",
    ("storage.k8s.io/v1beta1", "CSIStorageCapacity"): "1.27",
}
GONE_KINDS = {"PodSecurityPolicy": "1.25"}
VERSIONS = ("1.35", "1.36", "1.37")
KEYWORDS = {
    3: (("deprecated", "removed", "gỡ"), ("pluto", "kubent", "kubectl convert", "deprecated api"), ("etcd",),
        ("snapshot", "backup"), ("pdb", "poddisruptionbudget"), ("release notes", "changelog"), ("staging",)),
    4: (("kubeadm upgrade plan",), ("kubeadm upgrade apply",), ("kubeadm upgrade node",)),
    5: (("drain",), ("uncordon",), ("pdb", "poddisruptionbudget"), ("surge", "node mới", "thay node", "node pool")),
    6: (("etcd",), ("restore",), ("downgrade", "không hạ", "không lùi")),
    7: (("smoke",), ("slo", "error budget", "tỉ lệ lỗi"), ("thông báo", "status page", "kênh")),
}
MIN_BULLETS = {3: 5, 4: 4, 5: 4, 6: 3, 7: 4}


def manifests() -> list[dict]:
    return [d for f in sorted(ex.path("manifests").glob("*.yaml")) for d in yaml.safe_load_all(f.read_text(encoding="utf-8")) if d]


def removed_problems(docs) -> list[str]:
    found = []
    for doc in docs:
        key = (doc.get("apiVersion"), doc.get("kind"))
        name = f"{doc.get('kind')} {doc.get('metadata', {}).get('name')}"
        if key in REMOVED:
            found.append(f"{name}: {key[0]} đã bị gỡ từ Kubernetes {REMOVED[key]}")
        elif doc.get("kind") in GONE_KINDS:
            found.append(f"{name}: kind {doc['kind']} đã bị gỡ hẳn từ {GONE_KINDS[doc['kind']]}, thay bằng Pod Security Admission")
    return found


def test_no_removed_api_versions():
    found = removed_problems(manifests())
    assert not found, "\n".join(found)


def test_removed_table_catches_starter_legacy():
    legacy = [d for f in sorted((ex.dir / "starter" / "manifests").glob("*.yaml"))
              for d in yaml.safe_load_all(f.read_text(encoding="utf-8")) if d]
    found = "\n".join(removed_problems(legacy))
    for needle in ("Ingress shop", "CronJob revenue-report", "PodDisruptionBudget api", "HorizontalPodAutoscaler api",
                   "PodSecurityPolicy olist-restricted"):
        assert needle in found, f"Bảng API phải bắt được {needle}"


def test_ingress_v1_shape():
    ingresses = [d for d in manifests() if d.get("kind") == "Ingress"]
    assert ingresses, "Giữ Ingress shop"
    for ingress in ingresses:
        assert ingress["spec"].get("ingressClassName") == "devops-traefik", "Dùng spec.ingressClassName thay annotation cũ"
        assert "kubernetes.io/ingress.class" not in (ingress["metadata"].get("annotations") or {})
        for rule in ingress["spec"]["rules"]:
            for path in rule["http"]["paths"]:
                assert path.get("pathType") in ("Prefix", "Exact", "ImplementationSpecific"), "networking.k8s.io/v1 bắt buộc pathType"
                assert set(path["backend"]) == {"service"}, "backend v1 là service.name và service.port"


def test_workloads_kept():
    kinds = sorted((d["kind"], d["metadata"]["name"]) for d in manifests())
    assert kinds == [("CronJob", "revenue-report"), ("Deployment", "api"), ("HorizontalPodAutoscaler", "api"), ("Ingress", "shop"),
                     ("PodDisruptionBudget", "api"), ("Service", "api")], kinds


def test_manifests_valid_on_current_cluster(tmp_path):
    ex.require_cluster()
    docs = manifests()
    with KubeLab() as lab:
        text = json.dumps(docs).replace(PLACEHOLDER, lab.hostname)
        docs = json.loads(text)
        problems = kube_manifest_problems(docs, lab_id=lab.id, namespace=lab.namespace)
        assert not problems, "\n".join(problems)
        failed = []
        for doc in docs:
            result = lab.kubectl("apply", "--dry-run=server", "-f", "-", input=json.dumps(doc), check=False)
            if result.returncode != 0:
                failed.append(f"{doc['kind']} {doc['metadata']['name']}: {result.stderr.strip()[-300:]}")
        assert not failed, "kubectl apply --dry-run=server trên cluster 1.34:\n" + "\n".join(failed)


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```"))).strip()


def plan_problems(doc: str, versions=VERSIONS) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(section(doc, 1))) < 300:
        found.append("Phần 1: bối cảnh cần ít nhất 300 ký tự")
    order = section(doc, 2)
    positions = [order.find(v) for v in versions]
    if -1 in positions or positions != sorted(positions):
        found.append(f"Phần 2: nêu lần lượt từng minor {' → '.join(versions)}")
    if "skew" not in order.lower():
        found.append("Phần 2: chưa nói tới version skew")
    if "```mermaid" not in section(doc, 5):
        found.append("Phần 5: cần một khối mermaid")
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = section(doc, number).lower()
        for group in groups:
            if not any(word in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


def test_upgrade_plan():
    found = plan_problems(ex.read("UPGRADE-PLAN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = plan_problems((FIXTURES / "UPGRADE-PLAN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and "Phần 5: cần một khối mermaid" in found


def test_checks_catch_weak_plan():
    found = "\n".join(plan_problems((FIXTURES / "UPGRADE-PLAN.weak.md").read_text(encoding="utf-8")))
    for needle in ("lần lượt từng minor", "version skew", "chưa nói tới etcd", "kubeadm upgrade node", "chưa nói tới uncordon",
                   "downgrade", "Phần 7: ít nhất 4"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_plan_passes():
    found = plan_problems((FIXTURES / "UPGRADE-PLAN.good.md").read_text(encoding="utf-8"), ("1.34", "1.35", "1.36"))
    assert not found, "\n".join(found)
