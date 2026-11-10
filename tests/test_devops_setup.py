import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

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


def test_mailpit_ports_bind_loopback_only():
    mappings = [str(m) for m in _services()["mailpit"]["ports"]]
    assert mappings == ["127.0.0.1:${MAILPIT_SMTP_PORT:-11025}:1025", "127.0.0.1:${MAILPIT_HTTP_PORT:-18025}:8025"]


def test_mailpit_registered_in_testkit():
    assert testkit.SERVICES["mailpit"] == ("MAILPIT_HOST", "localhost", "MAILPIT_SMTP_PORT", 11025)


def test_existing_service_images_unchanged():
    services = _services()
    for name, image in EXISTING_IMAGES.items():
        assert services[name]["image"] == image


DOC_LINK = re.compile(r"\]\((\.\./tracks/devops/[^)#\s]+)(?:#([^)\s]*))?\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
MODULES_DIR = ROOT / "tracks" / "devops" / "modules"


def github_slug(heading: str) -> str:
    """Slug của heading theo cách GitHub tạo anchor: chữ thường, giữ chữ (kể cả tiếng Việt), số, `-`, `_`; khoảng trắng thành `-`."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = unicodedata.normalize("NFC", re.sub(r"[`*]", "", text)).lower()
    kept = "".join(c for c in text if c in " -_" or unicodedata.category(c)[0] in "LNM")
    return kept.replace(" ", "-")


def heading_slugs(markdown: str) -> set[str]:
    slugs: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    for line in markdown.splitlines():
        if line.strip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        match = None if in_fence else HEADING.match(line)
        if match:
            slug = github_slug(match.group(1))
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            slugs.add(slug if count == 0 else f"{slug}-{count}")
    return slugs


def devops_link_problems(text: str, base: Path, modules_dir: Path) -> list[str]:
    """Link tới tracks/devops phải trỏ tới tệp có thật và anchor khớp một heading.

    Chỉ bỏ qua link tới module chưa có thư mục (module của phase sau).
    """
    found = []
    for link, anchor in DOC_LINK.findall(text):
        target = (base / link).resolve()
        if target.is_relative_to(modules_dir.resolve()):
            module_id = target.relative_to(modules_dir.resolve()).parts[0]
            if not (modules_dir / module_id).is_dir():
                continue
        if not target.is_file():
            found.append(f"{link}: tệp không tồn tại")
            continue
        if anchor:
            wanted = unicodedata.normalize("NFC", unquote(anchor)).lower()
            if wanted not in heading_slugs(target.read_text(encoding="utf-8")):
                found.append(f"{link}#{anchor}: không có heading nào tạo anchor này")
    return found


def test_devops_tools_links_point_to_existing_headings():
    text = TOOLS_DOC.read_text(encoding="utf-8")
    assert DOC_LINK.findall(text)
    assert devops_link_problems(text, TOOLS_DOC.parent, MODULES_DIR) == []


def test_github_slug_rules():
    assert github_slug("0. Cài đặt") == "0-cài-đặt"
    assert github_slug("2. Cấu hình Nginx: server, location, proxy_pass và header") == "2-cấu-hình-nginx-server-location-proxy_pass-và-header"
    assert github_slug("Ghim CPU trên máy dùng chung") == "ghim-cpu-trên-máy-dùng-chung"
    assert github_slug("`nginx -t` và [docs](https://x)") == "nginx--t-và-docs"
    assert github_slug(unicodedata.normalize("NFD", "Cài đặt")) == "cài-đặt"


def test_link_check_catches_bad_anchor_and_missing_file(tmp_path):
    modules = tmp_path / "tracks" / "devops" / "modules"
    readme = modules / "05-web-server-proxy" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# M\n\n## 0. Cài đặt\n\n```bash\n## 9. Không phải heading\n```\n\n## 1. Phần một\n\n## 1. Phần một\n", encoding="utf-8")
    base = tmp_path / "setup"
    base.mkdir()
    good = (
        "[a](../tracks/devops/modules/05-web-server-proxy/README.md#0-cài-đặt) "
        "[b](../tracks/devops/modules/05-web-server-proxy/README.md#0-c%C3%A0i-%C4%91%E1%BA%B7t) "
        "[c](../tracks/devops/modules/05-web-server-proxy/README.md#1-phần-một-1) "
        "[d](../tracks/devops/modules/12-gitops-secrets/README.md#0-cài-đặt)"
    )
    assert devops_link_problems(good, base, modules) == []
    bad_anchor = "[x](../tracks/devops/modules/05-web-server-proxy/README.md#0-cai-dat)"
    assert any("0-cai-dat" in p for p in devops_link_problems(bad_anchor, base, modules))
    fenced = "[x](../tracks/devops/modules/05-web-server-proxy/README.md#9-không-phải-heading)"
    assert devops_link_problems(fenced, base, modules)
    missing = "[x](../tracks/devops/modules/05-web-server-proxy/INSTALL.md#0-cài-đặt)"
    assert any("không tồn tại" in p for p in devops_link_problems(missing, base, modules))


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


def test_registry_service_loopback():
    registry = _services()["registry"]
    assert re.fullmatch(r"registry:2\.\d+\.\d+", registry["image"]), registry["image"]
    assert registry["profiles"] == ["devops"]
    assert [str(m) for m in registry["ports"]] == ["127.0.0.1:${DEVOPS_REGISTRY_PORT:-15000}:5000"]
    assert registry["cpuset"] == "${DEVOPS_CPUSET:-}"
    assert str(registry["environment"]["REGISTRY_STORAGE_DELETE_ENABLED"]).lower() == "true"
    assert 15000 not in RESERVED_PORTS


def test_registry_registered_in_testkit():
    assert testkit.SERVICES["registry"] == ("REGISTRY_HOST", "localhost", "DEVOPS_REGISTRY_PORT", 15000)


def test_env_example_lists_registry_port():
    assert "# DEVOPS_REGISTRY_PORT=15000" in (ROOT / "setup" / ".env.example").read_text(encoding="utf-8").splitlines()


def test_devops_tools_documents_act_and_registry():
    text = TOOLS_DOC.read_text(encoding="utf-8")
    assert "| act |" in text and testkit.ACT_MIN_VERSION in text and testkit.ACT_IMAGE in text
    assert "up -d registry" in text and "DEVOPS_REGISTRY_PORT" in text


ACT_RUNNER = ROOT / "setup" / "act-runner"


def test_act_runner_base_is_pinned_by_digest():
    text = (ACT_RUNNER / "Dockerfile").read_text(encoding="utf-8")
    bases = re.findall(r"^FROM\s+(\S+)", text, re.M)
    assert len(bases) == 1
    assert re.fullmatch(rf"{re.escape(testkit.ACT_BASE_IMAGE)}@sha256:[0-9a-f]{{64}}", bases[0])


def test_act_runner_tag_follows_inputs():
    import hashlib

    text = (ACT_RUNNER / "Dockerfile").read_text(encoding="utf-8")
    version = re.search(r'devops-track\.act-runner="([^"]+)"', text).group(1)
    content = (ACT_RUNNER / "Dockerfile").read_bytes() + (ACT_RUNNER / "requirements-ci.txt").read_bytes()
    expected = f"devops-track/act-runner:{version}-{hashlib.sha256(content).hexdigest()[:8]}"
    assert testkit.ACT_IMAGE == expected, (
        f"Tag image runner phải theo nội dung setup/act-runner: {expected}. Build lại bằng: {testkit.ACT_IMAGE_BUILD}")
    assert "UV_OFFLINE=1" in text and "UV_PYTHON_DOWNLOADS=never" in text


def test_act_runner_build_command_matches_readme():
    build = testkit.ACT_IMAGE_BUILD
    digest = re.search(r"^FROM\s+\S+@(sha256:[0-9a-f]{64})", (ACT_RUNNER / "Dockerfile").read_text(encoding="utf-8"), re.M).group(1)
    for piece in (f"grep -qx 'node@{digest}'", "nice -n 15 docker build --pull=false", '${DEVOPS_CPUSET:+--cpuset-cpus "$DEVOPS_CPUSET"}',
                  f"-t {testkit.ACT_IMAGE} setup/act-runner"):
        assert piece in build, piece
    readme = (ROOT / "tracks" / "devops" / "modules" / "07-cicd-artifacts" / "README.md").read_text(encoding="utf-8")
    assert ('ACT_RUNNER="devops-track/act-runner:1.0-$(cat setup/act-runner/Dockerfile setup/act-runner/requirements-ci.txt '
            '| sha256sum | cut -c1-8)"') in readme
    assert f"'node@{digest}'" in readme and '-t "$ACT_RUNNER" setup/act-runner' in readme
    assert testkit.ACT_IMAGE in readme, (
        f"README module 07 phải in tag hiện tại {testkit.ACT_IMAGE} trong output mẫu và ~/.actrc; cập nhật sau khi build lại")


def test_act_runner_caches_every_sample_app_requirement():
    cached = set((ACT_RUNNER / "requirements-ci.txt").read_text(encoding="utf-8").split())
    app = (ROOT / "tracks" / "devops" / "sample-app" / "requirements.txt").read_text(encoding="utf-8").split()
    assert set(app) <= cached
    for dev in ROOT.glob("tracks/devops/modules/*/exercises/*/*/tests/fixtures/repo/requirements-dev.txt"):
        assert set(dev.read_text(encoding="utf-8").split()) <= cached, dev


DE_LOCALSTACK_BLOCK = '''  localstack:
    # Giả lập API AWS (S3, IAM, STS...) trên máy local cho module 11-cloud, không tốn tiền.
    # Pin bản 4.x community: các bản mới hơn có thể yêu cầu LOCALSTACK_AUTH_TOKEN.
    image: localstack/localstack:4.4.0
    profiles: [cloud, all]
    environment:
      SERVICES: s3,iam,sts
      AWS_DEFAULT_REGION: us-east-1
    ports:
      - "${LOCALSTACK_PORT:-4566}:4566"
    volumes:
      - localstack_data:/var/lib/localstack
    healthcheck:
      test: ["CMD-SHELL", "curl -fs http://localhost:4566/_localstack/health > /dev/null || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 20
      start_period: 20s
'''


def test_de_localstack_block_byte_identical():
    text = COMPOSE.read_text(encoding="utf-8")
    assert text.count(DE_LOCALSTACK_BLOCK + "\n") == 1
    assert text.endswith("  localstack_data:\n  devops_localstack_data:\n    name: devops-track-localstack-data\n")


def test_env_example_lists_localstack_devops_port():
    assert "# LOCALSTACK_DEVOPS_PORT=14566" in (ROOT / "setup" / ".env.example").read_text(encoding="utf-8").splitlines()


def test_devops_tools_documents_tofu_and_localstack_devops():
    text = TOOLS_DOC.read_text(encoding="utf-8")
    assert "| tofu (OpenTofu) |" in text and testkit.TOFU_MIN_VERSION in text and testkit.TOFU_VERSION in text
    assert testkit.LOCALSTACK_DEVOPS_START in text and "rm -fsv localstack-devops" in text
    assert "docker volume rm devops-track-localstack-data" in text and testkit.TOFU_AWS_PROVIDER in text
