import yaml
import pytest

import testkit
from quillo.config import PRODUCT_DIR

HELM_IMAGE = "alpine/helm:3.22.1@sha256:8191701ad1f82ee3695c87211fcbfe6d7b1bb7df92ac1c8de9ccdb0995a6a2c1"
CHART = PRODUCT_DIR / "chart" / "quillo"
RESTRICTED = PRODUCT_DIR / "chart" / "examples" / "values-restricted.yaml"
QUOTA = {"requests.cpu": 3.0, "requests.memory": 4 * 1024**3, "limits.memory": 5 * 1024**3, "pods": 12}
POD_MAX = {"cpu": 2.0, "memory": 3 * 1024**3}
NODE_CPU_FREE = 1.5
UNITS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3}


def quantity(value) -> float:
    text = str(value)
    if text.endswith("m"):
        return float(text[:-1]) / 1000
    for suffix, factor in UNITS.items():
        if text.endswith(suffix):
            return float(text[:-2]) * factor
    return float(text)


@pytest.fixture(scope="module")
def helm():
    if not testkit.docker_ready():
        pytest.skip("Cần Docker để chạy helm trong container (testkit.DockerLab)")
    testkit.Exercise.require_image(HELM_IMAGE)
    assert (CHART / "Chart.yaml").is_file() and RESTRICTED.is_file(), "thiếu chart/quillo hoặc chart/examples"
    with testkit.DockerLab() as lab:
        def run(*args: str):
            mounts = [(PRODUCT_DIR / "chart", "/charts")]
            return lab.run_once("helm", HELM_IMAGE, *args, mounts=mounts, timeout=120)
        yield run


def render(helm, *values: str) -> list[dict]:
    result = helm("template", "quillo", "/charts/quillo", "--namespace", "quillo", *values)
    assert result.returncode == 0, result.stderr
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def pods(docs: list[dict]) -> dict[str, dict]:
    return {d["metadata"]["name"]: d["spec"]["template"]["spec"] for d in docs
            if d["kind"] in {"Deployment", "StatefulSet"}}


def containers(spec: dict) -> list[dict]:
    return spec.get("initContainers", []) + spec["containers"]


def test_chart_version_follows_app():
    chart = yaml.safe_load((CHART / "Chart.yaml").read_text())
    from quillo import __version__

    assert chart["name"] == "quillo" and chart["version"] == chart["appVersion"] == __version__


def test_chart_renders_and_lints(helm):
    for extra in ([], ["-f", "/charts/examples/values-restricted.yaml"]):
        lint = helm("lint", "/charts/quillo", *extra)
        assert lint.returncode == 0, lint.stdout + lint.stderr
    docs = render(helm)
    kinds = sorted({d["kind"] for d in docs})
    assert kinds == ["Deployment", "PersistentVolumeClaim", "Secret", "Service", "StatefulSet"]
    assert set(pods(docs)) == {"quillo-api", "quillo-worker", "quillo-db", "quillo-llm", "quillo-embed"}
    assert all(d["metadata"].get("namespace", "quillo") == "quillo" for d in docs)
    for name, spec in pods(docs).items():
        assert "securityContext" not in spec, name
        for c in containers(spec):
            assert "securityContext" not in c and "resources" not in c, (name, c["name"])
        assert not any("hostPath" in v for v in spec.get("volumes", [])), name
    for name in ("quillo-llm", "quillo-embed"):
        init = pods(docs)[name]["initContainers"]
        assert [c["image"] for c in init] == ["quillo-models:1.1.0"]
    api = pods(docs)["quillo-api"]["containers"][0]
    assert api["image"] == "quillo-api:1.1.0" and api["imagePullPolicy"] == "IfNotPresent"

    restricted = render(helm, "-f", "/charts/examples/values-restricted.yaml")
    assert "NetworkPolicy" not in {d["kind"] for d in restricted}
    total = {"requests.cpu": 0.0, "requests.memory": 0.0, "limits.memory": 0.0}
    for name, spec in pods(restricted).items():
        context = spec.get("securityContext", {})
        assert context.get("seccompProfile", {}).get("type") == "RuntimeDefault", name
        pod_limits = {"cpu": 0.0, "memory": 0.0}
        for c in containers(spec):
            sc = {**context, **c.get("securityContext", {})}
            assert sc.get("runAsNonRoot") is True and sc.get("runAsUser", 1) != 0, (name, c["name"])
            assert c["securityContext"]["allowPrivilegeEscalation"] is False, (name, c["name"])
            assert c["securityContext"]["capabilities"]["drop"] == ["ALL"], (name, c["name"])
            assert c["image"].startswith("10.0.2.101:5000/"), c["image"]
            res = c["resources"]
            for kind in ("requests", "limits"):
                assert {"cpu", "memory"} <= set(res[kind]), (name, c["name"], kind)
            if c in spec["containers"]:
                total["requests.cpu"] += quantity(res["requests"]["cpu"])
                total["requests.memory"] += quantity(res["requests"]["memory"])
                total["limits.memory"] += quantity(res["limits"]["memory"])
                pod_limits["cpu"] += quantity(res["limits"]["cpu"])
                pod_limits["memory"] += quantity(res["limits"]["memory"])
        assert all(pod_limits[k] <= POD_MAX[k] for k in POD_MAX), (name, pod_limits)
    assert all(total[k] <= QUOTA[k] for k in total), total
    assert total["requests.cpu"] <= NODE_CPU_FREE, "lawfirm-prod có 2 vCPU, pod hệ thống k3s đã giữ một phần"
    pvcs = [d for d in restricted if d["kind"] == "PersistentVolumeClaim"]
    pvcs += [t for d in restricted if d["kind"] == "StatefulSet" for t in d["spec"].get("volumeClaimTemplates", [])]
    assert pvcs and all(quantity(p["spec"]["resources"]["requests"]["storage"]) <= 10 * 1024**3 for p in pvcs)


def test_chart_options_render(helm):
    docs = render(helm, "--set", "networkPolicy.enabled=true", "--set", "oidc.issuer=http://10.0.2.102:8080/realms/lawfirm",
                  "--set", "oidc.existingSecret=quillo-oidc", "--set", "acl=legal:legal/",
                  "--set", "extensions.configMap=acme-ext", "--set", "extensions.modules={acme_report}",
                  "--set", "image.registry=registry.lan:5000", "--set", "auth.existingSecret=quillo-auth")
    kinds = {d["kind"] for d in docs}
    assert "NetworkPolicy" in kinds and "Secret" not in kinds
    api = pods(docs)["quillo-api"]
    env = {e["name"]: e for e in api["containers"][0]["env"]}
    assert env["QUILLO_OIDC_ISSUER"]["value"] == "http://10.0.2.102:8080/realms/lawfirm"
    assert env["QUILLO_OIDC_CLIENT_SECRET_FILE"]["value"].startswith("/etc/quillo/oidc/")
    assert env["QUILLO_ACL"]["value"] == "legal:legal/"
    assert env["QUILLO_EXTENSIONS"]["value"] == "acme_report"
    assert env["QUILLO_ADMIN_TOKEN"]["valueFrom"]["secretKeyRef"]["name"] == "quillo-auth"
    volumes = {v["name"]: v for v in api["volumes"]}
    assert volumes["oidc"]["secret"]["secretName"] == "quillo-oidc"
    assert volumes["extensions"]["configMap"]["name"] == "acme-ext"
    images = {c["image"] for spec in pods(docs).values() for c in containers(spec)}
    assert images == {"registry.lan:5000/quillo-api:1.1.0", "registry.lan:5000/quillo-models:1.1.0",
                      "registry.lan:5000/pgvector/pgvector:0.8.6-pg16",
                      "registry.lan:5000/ggml-org/llama.cpp:server-b11718"}
