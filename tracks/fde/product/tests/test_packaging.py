import yaml

import release
from quillo.config import PRODUCT_DIR


def test_requirements_yaml():
    spec = yaml.safe_load((PRODUCT_DIR / "REQUIREMENTS.yaml").read_text())
    assert spec == {
        "min_cpus": 2,
        "min_mem_mb": 4096,
        "min_disk_free_gb": 10,
        "os": [{"id": "ubuntu", "min": "20.04"}, {"id": "rocky", "min": "8"}, {"id": "debian", "min": "11"}],
        "runtime": ["docker>=20.10", "podman>=4.0"],
        "ports": [18080],
        "gpu": "optional",
    }


def test_compose_only_api_publishes_on_loopback():
    compose = yaml.safe_load((PRODUCT_DIR / "compose.yaml").read_text())
    services = compose["services"]
    assert set(services) == {"db", "llm", "embed", "api", "worker"}
    assert [name for name, svc in services.items() if svc.get("ports")] == ["api"]
    assert services["api"]["ports"] == ["${QUILLO_BIND:-127.0.0.1}:${QUILLO_PORT:-18080}:8080"]
    assert services["worker"]["command"] == ["python", "-m", "quillo.ingest", "--watch", "/data/inbox"]
    assert services["worker"]["image"] == services["api"]["image"]
    for name in ("llm", "embed"):
        assert services[name]["image"] == release.tag_only(release.IMAGES["llm"])
        assert "./models:/models:ro" in services[name]["volumes"]
    assert services["db"]["image"] == release.tag_only(release.IMAGES["db"])
    assert "--embeddings" in services["embed"]["command"]


def test_images_pinned_by_digest():
    for ref in release.IMAGES.values():
        name, digest = ref.split("@")
        assert ":" in name and digest.startswith("sha256:") and len(digest) == 71
    dockerfile = (PRODUCT_DIR / "Dockerfile").read_text()
    assert "@sha256:" in dockerfile.splitlines()[0]
    assert "\nUSER 10001" in dockerfile


def test_env_example_has_only_placeholders():
    values = dict(line.split("=", 1) for line in (PRODUCT_DIR / ".env.example").read_text().splitlines()
                  if line and not line.startswith("#"))
    assert values["QUILLO_ADMIN_TOKEN"] == "" and values["QUILLO_DB_PASSWORD"] == ""
    assert values["QUILLO_VERSION"] == "1.1.0"


def test_htmx_is_vendored():
    static = PRODUCT_DIR / "src" / "quillo" / "static" / "htmx.min.js"
    assert static.stat().st_size > 40_000
    for template in (PRODUCT_DIR / "src" / "quillo" / "templates").glob("*.html"):
        assert "://" not in template.read_text(), template


def test_bundle_migrations_follow_release():
    assert [p.name for p in release.migrations_for("1.0.0")] == ["0001_init.sql"]
    assert [p.name for p in release.migrations_for("1.1.0")] == ["0001_init.sql", "0002_v1_1_tags.sql"]
