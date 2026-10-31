import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import testkit  # noqa: E402

COMPOSE = ROOT / "setup" / "docker-compose.yml"
TOOLS_DOC = ROOT / "setup" / "DEVOPS-TOOLS.md"
RESERVED_PORTS = {5432, 6379, 9000, 9001, 8000, 8080}

EXISTING_IMAGES = {
    "postgres": "postgres:16.9",
    "mongo": "mongo:7.0.21",
    "redis": "redis:7.4.5",
    "cassandra": "cassandra:5.0.4",
    "neo4j": "neo4j:5.26.10",
    "minio": "pgsty/minio:RELEASE.2026-08-04T00-00-00Z",
    "kafka": "apache/kafka:3.9.1",
    "metabase": "metabase/metabase:v0.55.9",
    "superset": "de-learning-superset:6.1.0",
    "localstack": "localstack/localstack:4.4.0",
}


def _services():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]


def test_mailpit_profile_is_devops_only():
    assert _services()["mailpit"]["profiles"] == ["devops"]


def test_mailpit_image_is_pinned():
    image = _services()["mailpit"]["image"]
    assert image.startswith("axllent/mailpit:")
    assert image.split(":", 1)[1] not in ("", "latest")


def test_mailpit_host_ports_avoid_reserved():
    for mapping in _services()["mailpit"]["ports"]:
        host_port = int(re.search(r"\$\{[A-Z_]+:-(\d+)\}", str(mapping)).group(1))
        assert host_port not in RESERVED_PORTS


def test_mailpit_registered_in_testkit():
    assert testkit.SERVICES["mailpit"] == ("MAILPIT_HOST", "localhost", "MAILPIT_SMTP_PORT", 11025)


def test_existing_service_images_unchanged():
    services = _services()
    for name, image in EXISTING_IMAGES.items():
        assert services[name]["image"] == image


def test_devops_tools_links_point_to_existing_files():
    text = TOOLS_DOC.read_text(encoding="utf-8")
    links = re.findall(r"\]\((\.\./tracks/devops/[^)#]+)(?:#[^)]*)?\)", text)
    assert links
    for link in links:
        target = (TOOLS_DOC.parent / link).resolve()
        module_dir = target.parent
        if module_dir.exists():
            assert target.exists(), link


MODULE_LINK = re.compile(r"tracks/devops/modules/([^/)#\s]+)")


def undeclared_module_links(text: str, declared: set[str]) -> list[str]:
    return sorted({m for m in MODULE_LINK.findall(text) if m not in declared})


def _declared_modules() -> set[str]:
    data = json.loads((ROOT / "tracks" / "devops" / "track.json").read_text(encoding="utf-8"))
    return {m["id"] for m in data["modules"]}


def test_devops_tools_links_use_declared_module_ids():
    assert undeclared_module_links(TOOLS_DOC.read_text(encoding="utf-8"), _declared_modules()) == []


def test_undeclared_module_link_detection():
    declared = _declared_modules()
    bad = "[Cài đặt](../tracks/devops/modules/04-networking-dns/README.md#0-cài-đặt)"
    assert undeclared_module_links(bad, declared) == ["04-networking-dns"]
    good = "[Cài đặt](../tracks/devops/modules/04-networking-protocols/README.md#0-cài-đặt)"
    assert undeclared_module_links(good, declared) == []


HARDCODED_CPUSET = re.compile(r"(?:taskset\s+-c|--cpuset-cpus[\s=])\s*[\"']?\d")


def hardcoded_cpuset_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if HARDCODED_CPUSET.search(line)]


def test_cpu_pinning_guidance_uses_devops_cpuset():
    docs = [TOOLS_DOC, *sorted((ROOT / "tracks" / "devops").rglob("*.md"))]
    found = [f"{p.relative_to(ROOT)}: {line}" for p in docs for line in hardcoded_cpuset_lines(p.read_text(encoding="utf-8"))]
    assert found == []


def test_hardcoded_cpuset_detection():
    assert hardcoded_cpuset_lines("nice -n 15 taskset -c 12-35 kind create cluster")
    assert hardcoded_cpuset_lines("docker update --cpuset-cpus 12-35 devops-lab-control-plane")
    assert hardcoded_cpuset_lines('act --container-options "--cpuset-cpus=12-35"')
    assert hardcoded_cpuset_lines('nice -n 15 taskset -c "$DEVOPS_CPUSET" kind create cluster') == []
    assert hardcoded_cpuset_lines('docker update --cpuset-cpus "$DEVOPS_CPUSET" x') == []


CPUSET_NONE = re.compile(r"DEVOPS_CPUSET\s*=\s*[\"']?none\b|`none`")


def cpuset_none_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if "DEVOPS_CPUSET" in line and CPUSET_NONE.search(line)]


def test_docs_do_not_recommend_cpuset_none():
    docs = [TOOLS_DOC, *sorted((ROOT / "tracks" / "devops").rglob("*.md"))]
    found = [f"{p.relative_to(ROOT)}: {line}" for p in docs for line in cpuset_none_lines(p.read_text(encoding="utf-8"))]
    assert found == []


def test_cpuset_none_detection():
    assert cpuset_none_lines("- Đặt `DEVOPS_CPUSET=none` để không ghim")
    assert cpuset_none_lines('export DEVOPS_CPUSET="none"')
    assert cpuset_none_lines("ghim (`DEVOPS_CPUSET` rỗng hoặc `none`)")
    assert cpuset_none_lines("unset DEVOPS_CPUSET") == []
    assert cpuset_none_lines("export DEVOPS_CPUSET=2-7") == []
