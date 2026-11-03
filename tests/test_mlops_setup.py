import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mlopskit  # noqa: E402

COMPOSE = ROOT / "setup" / "mlops" / "compose.yaml"
ENV_EXAMPLE = ROOT / "setup" / ".env.example"
TAKEN_PORTS = {5432, 5433, 6379, 8000, 8080, 9000, 9001, 5000, 25432, 26379, 28000}
PORT_RE = re.compile(r"^\$\{(MLOPS_[A-Z_]+_PORT):-(\d+)\}$")


def _compose():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def _mappings():
    for name, svc in _compose()["services"].items():
        for mapping in svc.get("ports", []):
            host = str(mapping).rpartition(":")[0]
            yield name, str(mapping), host


def test_services_present():
    assert {"postgres", "minio", "minio-init", "mlflow"} <= set(_compose()["services"])


def test_images_pinned():
    for name, svc in _compose()["services"].items():
        if "image" not in svc or "build" in svc:
            continue
        tag = svc["image"].rpartition(":")[2]
        assert ":" in svc["image"] and tag != "latest", name


def test_ports_avoid_taken_defaults():
    found = 0
    for name, _, host in _mappings():
        found_port = re.search(r":-(\d+)\}", host)
        assert found_port, f"{name}: cổng sai dạng {host!r}"
        default = int(found_port.group(1))
        assert default not in TAKEN_PORTS, name
        found += 1
    assert found >= 3


def test_ports_bound_localhost():
    for name, mapping, _ in _mappings():
        assert mapping.startswith("127.0.0.1:"), name


def test_ports_from_env():
    seen = {}
    for name, _, host in _mappings():
        m = PORT_RE.match(host.removeprefix("127.0.0.1:"))
        assert m, f"{name}: {host}"
        seen[m.group(1)] = int(m.group(2))
    for service, (env_name, default) in mlopskit.STACK_SERVICES.items():
        assert seen.get(env_name) == default, service


def test_resource_limits_and_volumes():
    data = _compose()
    for name, svc in data["services"].items():
        assert svc.get("cpuset") == "${DEVOPS_CPUSET:-}", name
        assert "mem_limit" in svc, name
    assert data["volumes"] and all(v.startswith("mlops_") for v in data["volumes"])


def test_env_example_lists_mlops_ports():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for var in ("MLOPS_PG_PORT", "MLOPS_MINIO_PORT", "MLOPS_MINIO_CONSOLE_PORT", "MLOPS_MLFLOW_PORT"):
        assert var in text


def test_readme_documents_env_file():
    text = (ROOT / "setup" / "mlops" / "README.md").read_text(encoding="utf-8")
    assert "--env-file setup/.env" in text


def test_mlflow_allows_container_host_header():
    cmd = _compose()["services"]["mlflow"]["command"]
    flag = next(c for c in cmd if str(c).startswith("--allowed-hosts="))
    hosts = flag.split("=", 1)[1].split(",")
    assert {"mlflow", "mlflow:*", "localhost:*", "127.0.0.1:*"} <= set(hosts)


def test_profiles_declared():
    services = _compose()["services"]
    for name in ("prometheus", "alertmanager", "grafana"):
        assert services[name]["profiles"] == ["monitoring"], name
    assert services["redis"]["profiles"] == ["feast"]
    for name in ("postgres", "minio", "minio-init", "mlflow"):
        assert "profiles" not in services[name], name


def test_new_ports_avoid_taken_and_localhost():
    services = _compose()["services"]
    for name in ("prometheus", "alertmanager", "grafana", "redis"):
        for mapping in services[name]["ports"]:
            assert str(mapping).startswith("127.0.0.1:"), name
            default = int(re.search(r":-(\d+)\}", str(mapping)).group(1))
            assert default not in TAKEN_PORTS | {6379, 25000, 29000, 29001, 25433}, name
            assert default >= 20000, name


def test_new_services_pinned_and_provisioned():
    services = _compose()["services"]
    assert services["prometheus"]["image"] == "prom/prometheus:v3.5.0"
    assert services["grafana"]["image"] == "grafana/grafana:12.1.0"
    assert services["redis"]["image"] == "redis:7.4.5"
    datasource = (ROOT / "setup" / "mlops" / "monitoring" / "grafana" / "provisioning" / "datasources" / "prometheus.yml")
    assert "http://prometheus:9090" in datasource.read_text(encoding="utf-8")
    for name in ("prometheus.yml", "alertmanager.yml"):
        assert (ROOT / "setup" / "mlops" / "monitoring" / name).is_file()


def test_env_example_lists_phase2_ports():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for var in ("MLOPS_PROMETHEUS_PORT", "MLOPS_ALERTMANAGER_PORT", "MLOPS_GRAFANA_PORT", "MLOPS_REDIS_PORT"):
        assert var in text


def test_readme_documents_profiles():
    text = (ROOT / "setup" / "mlops" / "README.md").read_text(encoding="utf-8")
    assert "--profile monitoring --profile feast up -d --wait" in text


def test_helper_dockerfiles_present():
    assert "feast[redis]==0.67.0" in (ROOT / "setup" / "mlops" / "feast" / "Dockerfile").read_text(encoding="utf-8")
    assert (ROOT / "setup" / "mlops" / "act-runner" / "Dockerfile").is_file()


KIND_DIR = ROOT / "setup" / "mlops" / "kind"
ADDED_ON = "2026-11-04"
LATEST_RELEASE = "2026-10-21"


def _versions() -> dict[str, str]:
    values = {}
    for line in (KIND_DIR / "versions.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        values[key] = value
    return values


def test_kind_files_present():
    for name in ("cluster.yaml", "up.sh", "down.sh", "versions.env", "README.md", "argo-artifacts.yaml"):
        assert (KIND_DIR / name).is_file(), name


def test_versions_env_dates():
    values = _versions()
    components = sorted(k.removesuffix("_VERSION") for k in values if k.endswith("_VERSION"))
    assert {"KIND", "KUBECTL", "KUBERNETES", "CERT_MANAGER", "KSERVE", "ARGO", "ARGO_MINIO",
            "METRICS_SERVER", "KEDA", "KUEUE"} <= set(components)
    for component in components:
        released = values.get(f"{component}_RELEASED")
        assert released and re.fullmatch(r"\d{4}-\d{2}-\d{2}", released), component
        assert released <= LATEST_RELEASE, f"{component} phát hành {released}, chưa đủ 2 tuần trước {ADDED_ON}"
    for key, value in values.items():
        if key.endswith("_SHA256"):
            assert re.fullmatch(r"[0-9a-f]{64}", value), key


def test_cluster_yaml_pinned_and_local():
    cluster = yaml.safe_load((KIND_DIR / "cluster.yaml").read_text(encoding="utf-8"))
    assert cluster["name"] == mlopskit.KIND_CLUSTER
    assert len(cluster["nodes"]) == 1
    node = cluster["nodes"][0]
    assert node["image"] == _versions()["KIND_NODE_IMAGE"]
    assert re.fullmatch(r"kindest/node:v[\d.]+@sha256:[0-9a-f]{64}", node["image"])
    assert node["image"].startswith(f"kindest/node:{_versions()['KUBERNETES_VERSION']}@")
    ports = {m["hostPort"]: m for m in node["extraPortMappings"]}
    assert set(ports) == {28081, 28444}
    for mapping in ports.values():
        assert mapping["listenAddress"] == "127.0.0.1"
        assert mapping["hostPort"] not in TAKEN_PORTS


def test_up_sh_verifies_checksums_and_installs_locally():
    text = (KIND_DIR / "up.sh").read_text(encoding="utf-8")
    assert "sha256sum" in text and ".local/bin" in text
    assert "sudo" not in text and not re.search(r"curl[^\n]*\|\s*(ba)?sh", text)
    assert "MLOPS_KIND_HTTP_PORT" in text and "MLOPS_KIND_HTTPS_PORT" in text
    assert "RawDeployment" in text
    for key in ("KIND_SHA256", "KUBECTL_SHA256", "CERT_MANAGER_SHA256", "KSERVE_SHA256", "ARGO_SHA256"):
        assert key in text, key
    down = (KIND_DIR / "down.sh").read_text(encoding="utf-8")
    assert "delete cluster" in down and "mlops" in down


def test_env_example_lists_kind_ports():
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    assert "# MLOPS_KIND_HTTP_PORT=28081" in lines
    assert "# MLOPS_KIND_HTTPS_PORT=28444" in lines


def test_gpu_project_has_onnxruntime_gpu():
    text = (ROOT / "setup" / "gpu" / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'"onnxruntime-gpu==1\.\d+\.\d+"', text)
    lock = (ROOT / "setup" / "gpu" / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "onnxruntime-gpu"' in lock
    assert '{ name = "onnxruntime", marker = "sys_platform == \'never\'" }' in lock


def test_kind_checksums_per_arch():
    values = _versions()
    for tool in ("KIND", "KUBECTL"):
        for arch in ("AMD64", "ARM64"):
            assert re.fullmatch(r"[0-9a-f]{64}", values[f"{tool}_SHA256_{arch}"]), (tool, arch)
    text = (KIND_DIR / "up.sh").read_text(encoding="utf-8")
    assert "uname -m" in text and "kind-linux-${ARCH}" in text


@pytest.mark.parametrize("port", ["1;touch x", "80", "99999", "abc"])
def test_up_sh_rejects_bad_port(port):
    import os
    import subprocess

    env = {**os.environ, "MLOPS_KIND_HTTP_PORT": port, "HOME": "/nonexistent-mlops-test"}
    result = subprocess.run(["bash", str(KIND_DIR / "up.sh")], capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 1
    assert "cổng không hợp lệ" in result.stderr


def test_up_sh_restores_kube_context():
    text = (KIND_DIR / "up.sh").read_text(encoding="utf-8")
    assert "config current-context" in text and "trap restore_context EXIT" in text


def test_argo_artifacts_scoped_and_isolated():
    docs = list(yaml.safe_load_all((KIND_DIR / "argo-artifacts.yaml").read_text(encoding="utf-8")))
    by_kind = {(d["kind"], d["metadata"]["name"]): d for d in docs}
    images = [c["image"] for c in by_kind[("Deployment", "argo-artifacts")]["spec"]["template"]["spec"]["containers"]]
    assert images == [_versions()["ARGO_MINIO_IMAGE"], _versions()["ARGO_MC_IMAGE"]]
    secret = by_kind[("Secret", "argo-artifacts")]["stringData"]
    executor = by_kind[("ConfigMap", "workflow-controller-configmap")]["data"]["executor"]
    assert secret["accesskey"] not in executor and secret["secretkey"] not in executor
    env = {e["name"]: e["value"] for e in yaml.safe_load(executor)["env"]}
    assert env["AWS_ACCESS_KEY_ID"] == secret["workflow-accesskey"]
    assert env["AWS_SECRET_ACCESS_KEY"] == secret["workflow-secretkey"]
    template = by_kind[("Deployment", "argo-artifacts")]["spec"]["template"]["metadata"]
    assert template["annotations"]["mlops/config-sha256"] == "__CONFIG_SHA256__"
    up = (KIND_DIR / "up.sh").read_text(encoding="utf-8")
    assert 'sha256sum "$HERE/argo-artifacts.yaml"' in up and "__CONFIG_SHA256__" in up
    provision = by_kind[("ConfigMap", "argo-artifacts-provision")]["data"]["provision.sh"]
    assert "grep" not in provision
    policy = by_kind[("NetworkPolicy", "argo-artifacts")]["spec"]
    assert policy["policyTypes"] == ["Ingress"]
    keys = [e["key"] for rule in policy["ingress"] for src in rule["from"]
            for e in src.get("podSelector", {}).get("matchExpressions", [])]
    assert keys == ["workflows.argoproj.io/workflow"]


def test_kafka_service_pinned_local_and_healthchecked():
    kafka = _compose()["services"]["kafka"]
    assert kafka["profiles"] == ["streaming"]
    assert re.fullmatch(r"apache/kafka:4\.3\.1@sha256:[0-9a-f]{64}", kafka["image"])
    assert kafka["ports"] == ["127.0.0.1:${MLOPS_KAFKA_PORT:-29092}:9094"]
    assert 29092 not in TAKEN_PORTS | {6379, 25000, 29000, 29001, 25433, 29090, 29093, 23000, 26390}
    env = kafka["environment"]
    assert env["KAFKA_PROCESS_ROLES"] == "broker,controller"
    assert env["KAFKA_AUTO_CREATE_TOPICS_ENABLE"] == "false"
    assert "HOST://127.0.0.1:${MLOPS_KAFKA_PORT:-29092}" in env["KAFKA_ADVERTISED_LISTENERS"]
    assert "PLAINTEXT://kafka:9092" in env["KAFKA_ADVERTISED_LISTENERS"]
    assert "kafka-broker-api-versions.sh" in " ".join(kafka["healthcheck"]["test"])
    assert mlopskit.STACK_SERVICES["kafka"] == ("MLOPS_KAFKA_PORT", 29092)
    assert mlopskit.STACK_PROFILES["kafka"] == "streaming"


def test_env_example_ends_with_kafka_port():
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    assert lines[-1] == "# MLOPS_KAFKA_PORT=29092"


def test_readme_documents_streaming_profile():
    text = (ROOT / "setup" / "mlops" / "README.md").read_text(encoding="utf-8")
    assert "--profile streaming up -d --wait" in text and "MLOPS_KAFKA_PORT" in text


def test_up_sh_senior_addons_pinned():
    text = (KIND_DIR / "up.sh").read_text(encoding="utf-8")
    assert "--senior" in text
    for key in ("METRICS_SERVER_SHA256", "KEDA_SHA256", "KUEUE_SHA256"):
        assert f'"${key}"' in text, key
    assert "--kubelet-insecure-tls" in text and '"batch/job"' in text
    values = _versions()
    assert values["KEDA_VERSION"] == "v2.21.0" and values["KUEUE_VERSION"] == "v0.20.2"
    assert values["METRICS_SERVER_VERSION"] == "v0.9.0"
    readme = (KIND_DIR / "README.md").read_text(encoding="utf-8")
    assert "up.sh --senior" in readme and "+0,55 GiB" in readme


@pytest.mark.parametrize("arg", ["--bogus", "senior", "--senior=1"])
def test_up_sh_rejects_unknown_arg(arg):
    import os
    import subprocess

    env = {**os.environ, "HOME": "/nonexistent-mlops-test"}
    result = subprocess.run(["bash", str(KIND_DIR / "up.sh"), arg], capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 1
    assert "tham số không hợp lệ" in result.stderr


def test_up_sh_help():
    import subprocess

    result = subprocess.run(["bash", str(KIND_DIR / "up.sh"), "--help"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0 and "--senior" in result.stdout


def test_modelscan_dockerfile_pinned():
    folder = ROOT / "setup" / "mlops" / "modelscan"
    text = (folder / "Dockerfile").read_text(encoding="utf-8")
    assert re.match(r"FROM python:3\.12\.11-slim@sha256:[0-9a-f]{64}\n", text)
    assert "--require-hashes" in text and "requirements.txt" in text
    requirements = (folder / "requirements.txt").read_text(encoding="utf-8")
    entries = re.findall(r"^([a-z0-9-]+)==(\S+) \\\n((?:    --hash=sha256:[0-9a-f]{64}(?: \\)?\n)+)", requirements, flags=re.M)
    pins = {name: version for name, version, _ in entries}
    assert {"modelscan": "0.8.8", "numpy": "2.5.4", "rich": "14.3.4", "tomlkit": "0.13.3", "click": "8.5.0"}.items() <= pins.items()
    assert len(entries) == len(re.findall(r"^[a-z]", requirements, flags=re.M))


def test_mlops_senior_group_in_default_env():
    import tomllib

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "mlops-senior" in data["tool"]["uv"]["default-groups"]
    group = set(data["dependency-groups"]["mlops-senior"])
    assert {"ray[train,tune]==2.59.0", "river==0.26.1", "copier==9.19.1", "model-signing==1.1.1",
            "cyclonedx-bom==7.5.0", "pyopenssl==26.4.0"} == group
    assert not any(d.startswith("modelscan") for d in data["project"]["dependencies"] + sorted(group))
