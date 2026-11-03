import re
import sys
from pathlib import Path

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
