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
            host, _, container = str(mapping).rpartition(":")
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
        default = int(re.search(r":-(\d+)\}", host).group(1))
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
