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
