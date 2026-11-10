"""M03: container/Dockerfile (target api, worker), container/compose.yaml, container/trivy.yaml. Hợp đồng đầy đủ ở
capstone/milestones/m03-containers.md."""

import datetime as dt
import json
import re
import secrets
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest
import yaml

from olist_stack import (
    APP, COMPOSE, DOCKERFILE, FAKE_TOKEN, TARGETS, assemble, build_targets, leak_hashes, missing, require_trivy,
    require_trivy_db, trivy_image,
)
from testkit import DockerLab, Exercise

DOC = "m03-containers.md"
FIXTURES = Path(__file__).parent / "fixtures"
DEFECTIVE = FIXTURES / "defective"
BUILD_TOOLS = ("gcc", "cc", "g++", "c++", "make", "ld")
IMAGE_LIMIT_MB = 350
BASE_PINNED = re.compile(r"^[^@\s]+:[^@\s]*\d+\.\d+\.\d+[^@\s]*(@sha256:[0-9a-f]{64})?$|^[^@\s]+@sha256:[0-9a-f]{64}$")
INFRA_PINNED = re.compile(r"^[^@\s]+:\d+\.\d+[^@\s]*(@sha256:[0-9a-f]{64})?$|^[^@\s]+@sha256:[0-9a-f]{64}$")
REQUIRED_IMAGE = {"api": "OLIST_API_IMAGE", "worker": "OLIST_WORKER_IMAGE"}
NUMERIC_USER = re.compile(r"^[1-9]\d*(:\d+)?$")
BLOCKING = {"HIGH", "CRITICAL"}
IGNOREFILE = "container/.trivyignore.yaml"
PG_DATA_ROOT = "/var/lib/postgresql"


def pinned_requirements() -> dict[str, str]:
    found = {}
    for line in (APP / "requirements.txt").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?==([^\s;#]+)", line)
        if match:
            found[match.group(1).lower().replace("_", "-")] = match.group(2)
    return found

PROBE = r"""
import hashlib, json, os, shutil, sys
want = set(sys.argv[1].split(","))
tools = [t for t in sys.argv[2].split(",") if shutil.which(t)]
leaks = []
sites = set()
for top, dirs, files in os.walk("/"):
    dirs[:] = [d for d in dirs if os.path.join(top, d) not in ("/proc", "/sys", "/dev")]
    if any(d.startswith("redis-") and d.endswith(".dist-info") for d in dirs):
        sites.add(top)
    for name in files:
        if name in (".env", "test_api.py", "test_worker.py"):
            path = os.path.join(top, name)
            try:
                with open(path, "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
            except OSError:
                continue
            if digest in want:
                leaks.append(path)
deps = []
for site in sorted(sites):
    h = hashlib.sha256()
    for top, dirs, files in sorted(os.walk(site)):
        for name in sorted(files):
            st = os.lstat(os.path.join(top, name))
            h.update(f"{os.path.relpath(os.path.join(top, name), site)}|{st.st_size}|{int(st.st_mtime)}\n".encode())
    deps.append(site + "#" + h.hexdigest())
print(json.dumps({"uid": os.getuid(), "tools": tools, "leaks": sorted(leaks), "deps": deps}))
"""


def require_file(path: Path) -> Path:
    if not path.is_file():
        pytest.fail(missing(path, DOC), pytrace=False)
    return path


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}", pytrace=False)
    return data if isinstance(data, dict) else {}


def dockerfile_problems(text: str) -> list[str]:
    lines = [line.strip() for line in re.sub(r"\\\r?\n", " ", text).splitlines()]
    froms = [line.split()[1:] for line in lines if re.match(r"FROM\s", line, re.I)]
    froms = [[part for part in parts if not part.startswith("--")] for parts in froms]
    stages = {parts[2].lower() for parts in froms if len(parts) >= 3 and parts[1].lower() == "as"}
    found = []
    if len(froms) < 2:
        found.append("Dockerfile chỉ có 1 stage: cần stage build (cài dependency) tách khỏi stage runtime")
    for target in TARGETS:
        if target not in stages:
            found.append(f"Thiếu stage `{target}` (FROM ... AS {target}): test build bằng --target {target}")
    for parts in froms:
        ref = parts[0] if parts else ""
        if not ref or ref.lower() in stages or ref.lower() == "scratch" or "$" in ref:
            continue
        if not BASE_PINNED.match(ref):
            found.append(f"Image nền {ref} chưa ghim: dùng tag có đủ major.minor.patch (vd. python:3.12.16-slim-trixie) "
                         "hoặc digest @sha256:..., không dùng latest hay tag trôi như python:3.12-slim")
    return found


def health_test(config: dict) -> list[str]:
    test = (config.get("Healthcheck") or {}).get("Test") or []
    return [] if not test or test[0] == "NONE" else test


def shell_form(command) -> bool:
    return bool(command) and command[:2] in (["/bin/sh", "-c"], ["sh", "-c"])


def probe(lab: DockerLab, alias: str, tag: str) -> dict:
    result = lab.run_once(alias, tag, "-c", PROBE, ",".join(leak_hashes()), ",".join(BUILD_TOOLS), entrypoint="python3",
                          timeout=120)
    if result.returncode != 0:
        pytest.fail(f"Không chạy được python3 trong image {tag}: {result.stderr[-600:]}", pytrace=False)
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        pytest.fail(f"python3 trong image {tag} không in được kết quả kiểm tra: {result.stdout[-600:]}", pytrace=False)


def image_problems(lab: DockerLab, tag: str, target: str, version: str, revision: str, facts: dict) -> list[str]:
    info = lab.image_inspect(tag)
    config = info["Config"]
    found = []
    user = str(config.get("User") or "")
    if not NUMERIC_USER.match(user):
        found.append(f"{target}: USER phải là UID số khác 0 (vd. 10001:10001) để Kubernetes kiểm được runAsNonRoot, "
                     f"đang là {user or '(trống, tức root)'}")
    if facts["uid"] == 0:
        found.append(f"{target}: tiến trình trong container chạy với UID 0 (root)")
    if facts["tools"]:
        found.append(f"{target}: image cuối còn công cụ build: {', '.join(facts['tools'])}")
    entry, cmd = config.get("Entrypoint"), config.get("Cmd")
    if shell_form(entry) or (not entry and shell_form(cmd)):
        found.append(f"{target}: CMD/ENTRYPOINT dạng shell ({entry or cmd}): /bin/sh là PID 1 và nuốt SIGTERM")
    if not health_test(config):
        found.append(f"{target}: image không có HEALTHCHECK")
    labels = config.get("Labels") or {}
    for key, want in (("org.opencontainers.image.version", version), ("org.opencontainers.image.revision", revision)):
        if labels.get(key) != want:
            found.append(f"{target}: nhãn {key} phải bằng build arg ({want}), đang là {labels.get(key)!r}")
    if facts["leaks"]:
        found.append(f"{target}: image mang tệp không được có ở runtime (.env của máy dev, test): {', '.join(facts['leaks'])}")
    size = info["Size"] / 1e6
    if size > IMAGE_LIMIT_MB:
        found.append(f"{target}: image {size:.0f} MB, tối đa {IMAGE_LIMIT_MB} MB")
    return found


def duration_seconds(value) -> float:
    total = 0.0
    for amount, unit in re.findall(r"(\d+(?:\.\d+)?)(h|ms|m|s|us)", str(value or "")):
        total += float(amount) * {"h": 3600, "m": 60, "s": 1, "ms": 0.001, "us": 1e-6}[unit]
    return total


def ports_of(service: dict) -> list:
    return service.get("ports") or []


def loopback_8000(port) -> bool:
    if isinstance(port, dict):
        return str(port.get("host_ip")) == "127.0.0.1" and str(port.get("target")) == "8000"
    return bool(re.fullmatch(r"127\.0\.0\.1:(\$\{[^}]+\}|\d+):8000(/tcp)?", str(port)))


def depends_healthy(service: dict, name: str) -> bool:
    depends = service.get("depends_on")
    return isinstance(depends, dict) and (depends.get(name) or {}).get("condition") == "service_healthy"


def env_of(service: dict) -> dict:
    env = service.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) if "=" in item else (item, None) for item in env)
    return env


def compose_problems(data: dict, text: str) -> list[str]:
    services = data.get("services") if isinstance(data.get("services"), dict) else {}
    found = []
    for name in ("api", "worker", "postgres", "redis"):
        if not isinstance(services.get(name), dict):
            found.append(f"Thiếu service {name}")
    if found:
        return found
    for name, var in REQUIRED_IMAGE.items():
        svc = services[name]
        if not re.fullmatch(rf"\$\{{{var}:\?[^}}]+\}}", str(svc.get("image", ""))):
            found.append(f"{name}: image phải đúng dạng ${{{var}:?<thông báo>}}: compose production chạy đúng artifact đã "
                         f"build và quét, thiếu biến thì dừng ngay; đang là {svc.get('image')!r}")
        if svc.get("build"):
            found.append(f"{name}: compose production không build (bỏ build:)")
        if svc.get("read_only") is not True:
            found.append(f"{name}: cần read_only: true")
        if "/tmp" not in [str(t).split(":")[0] for t in (svc.get("tmpfs") if isinstance(svc.get("tmpfs"), list) else [svc.get("tmpfs")])]:
            found.append(f"{name}: cần tmpfs cho /tmp (root filesystem chỉ đọc)")
        if [str(c).upper() for c in svc.get("cap_drop") or []] != ["ALL"]:
            found.append(f"{name}: cần cap_drop: [ALL]")
        if svc.get("restart") not in ("unless-stopped", "always", "on-failure"):
            found.append(f"{name}: cần restart: unless-stopped (hoặc always, on-failure)")
        if not ((((svc.get("deploy") or {}).get("resources") or {}).get("limits")) or {}).get("memory"):
            found.append(f"{name}: cần deploy.resources.limits.memory")
        for dep in ("postgres", "redis"):
            if not depends_healthy(svc, dep):
                found.append(f"{name}: depends_on {dep} phải có condition: service_healthy")
        if "APP_VERSION" in env_of(svc):
            found.append(f"{name}: không đặt APP_VERSION trong compose; version đi theo image (build arg)")
        if "${POSTGRES_PASSWORD" not in str(env_of(svc).get("DATABASE_URL", "")):
            found.append(f"{name}: DATABASE_URL phải lấy mật khẩu từ ${{POSTGRES_PASSWORD...}}")
    if duration_seconds(services["worker"].get("stop_grace_period")) < 10:
        found.append("worker: cần stop_grace_period từ 10s trở lên (worker chờ BLPOP tối đa 5 giây trước khi thấy SIGTERM)")
    for name in ("postgres", "redis"):
        image = str(services[name].get("image", ""))
        if not INFRA_PINNED.match(image) or "latest" in image:
            found.append(f"{name}: image {image!r} chưa ghim: cần tag có ít nhất major.minor (vd. postgres:16.15-alpine) hoặc digest")
        if not (services[name].get("healthcheck") or {}).get("test"):
            found.append(f"{name}: cần healthcheck")
    password = str(env_of(services["postgres"]).get("POSTGRES_PASSWORD", ""))
    if not re.fullmatch(r"\$\{POSTGRES_PASSWORD:\?[^}]+\}", password):
        found.append("postgres: POSTGRES_PASSWORD phải là ${POSTGRES_PASSWORD:?<thông báo>}, không ghi mật khẩu trong tệp")
    volumes = [str(v.get("target") if isinstance(v, dict) else str(v).split(":")[1] if ":" in str(v) else "")
               for v in services["postgres"].get("volumes") or []]
    if not any(v == PG_DATA_ROOT or v.startswith(PG_DATA_ROOT + "/") for v in volumes):
        found.append(f"postgres: dữ liệu phải nằm trên named volume mount ở {PG_DATA_ROOT} hoặc thư mục con của nó "
                     "(postgres 16, 17: /var/lib/postgresql/data; postgres 18: /var/lib/postgresql)")
    for name, svc in services.items():
        if name == "api":
            if len(ports_of(svc)) != 1 or not loopback_8000(ports_of(svc)[0]):
                found.append("api: mở đúng một cổng, container 8000, chỉ trên 127.0.0.1 (vd. 127.0.0.1:${OLIST_SHOP_API_PORT:-28000}:8000)")
        elif ports_of(svc):
            found.append(f"{name}: không mở cổng ra máy host (chỉ api được mở)")
        logging = svc.get("logging") or {}
        if logging.get("driver") not in ("json-file", "local") or not (logging.get("options") or {}).get("max-size"):
            found.append(f"{name}: logging cần driver json-file hoặc local kèm options.max-size (xoay vòng log)")
    if re.search(r"olist:olist@|POSTGRES_PASSWORD:\s*['\"]?[A-Za-z0-9]", text):
        found.append("Tệp compose chứa mật khẩu dạng chữ")
    return found


def trivy_config_problems(data: dict) -> list[str]:
    found = []
    severity = data.get("severity")
    severity = severity.split(",") if isinstance(severity, str) else severity or []
    if {str(s).strip().upper() for s in severity} != BLOCKING:
        found.append(f"severity phải đúng HIGH và CRITICAL, đang là {data.get('severity')}")
    if not isinstance(data.get("exit-code"), int) or data.get("exit-code") == 0:
        found.append(f"exit-code phải khác 0 để gate làm pipeline đỏ, đang là {data.get('exit-code')}")
    if (data.get("vulnerability") or {}).get("ignore-unfixed") is not True:
        found.append("vulnerability.ignore-unfixed phải là true")
    if data.get("ignorefile") != IGNOREFILE:
        found.append(f"ignorefile phải là {IGNOREFILE} (đường dẫn tính từ gốc repo, nơi CI chạy trivy), đang là "
                     f"{data.get('ignorefile')}")
    scanners = set((data.get("scan") or {}).get("scanners") or [])
    if not {"vuln", "secret"} <= scanners:
        found.append(f"scan.scanners phải có vuln và secret, đang là {sorted(scanners)}")
    return found


def ignore_problems(data: dict) -> list[str]:
    found = []
    entries = data.get("vulnerabilities")
    if entries is None or not isinstance(entries, list):
        return ["`.trivyignore.yaml` cần khoá vulnerabilities là một danh sách (rỗng cũng được)"]
    for entry in entries:
        if not isinstance(entry, dict):
            found.append(f"Mục {entry!r} phải là mapping có id, purls, statement, expired_at")
            continue
        name = entry.get("id", "?")
        if not re.fullmatch(r"(CVE|GHSA)-[\w-]+", str(name)):
            found.append(f"{name}: id phải là CVE-... hoặc GHSA-...")
        if not entry.get("purls"):
            found.append(f"{name}: phải khoanh bằng purls (gói và phiên bản cụ thể)")
        if len(str(entry.get("statement") or "").strip()) < 40:
            found.append(f"{name}: statement phải giải thích vì sao chấp nhận (ít nhất 40 ký tự)")
        expiry = entry.get("expired_at")
        if not isinstance(expiry, (dt.date, dt.datetime)):
            try:
                dt.date.fromisoformat(str(expiry))
            except ValueError:
                found.append(f"{name}: thiếu expired_at dạng YYYY-MM-DD")
    return found


def without_expiry(data: dict) -> dict:
    for entry in data.get("vulnerabilities") or []:
        if isinstance(entry, dict):
            entry.pop("expired_at", None)
    return data


def findings(report: dict) -> list[dict]:
    return [v for r in report.get("Results") or [] for v in r.get("Vulnerabilities") or []]


def secret_findings(report: dict) -> list[str]:
    return [f"{r.get('Target')}: {s.get('RuleID')}" for r in report.get("Results") or [] for s in r.get("Secrets") or []]


def purl_ignored(vuln: dict, entries: list) -> bool:
    purl = ((vuln.get("PkgIdentifier") or {}).get("PURL") or "").split("?")[0]
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == vuln.get("VulnerabilityID"):
            purls = [str(p).split("?")[0] for p in entry.get("purls") or []]
            if not purls or purl in purls:
                return True
    return False


@dataclass
class Built:
    lab: DockerLab | None = None
    root: Path | None = None
    tags: dict = field(default_factory=dict)
    version: str = ""
    revision: str = ""
    facts: dict = field(default_factory=dict)
    error: str = ""

    def require(self) -> None:
        if self.error:
            pytest.fail(self.error, pytrace=False)


@dataclass
class Stack:
    project: object = None
    url: str = ""
    error: str = ""

    def require(self) -> None:
        if self.error:
            pytest.fail(self.error, pytrace=False)


@pytest.fixture(scope="module")
def built(project_root, tmp_path_factory):
    dockerfile = project_root / DOCKERFILE
    if not dockerfile.is_file():
        yield Built(error=missing(dockerfile, DOC))
        return
    Exercise.require_tool("docker")
    root = assemble(tmp_path_factory.mktemp("m03-repo"), project_root)
    version, revision = f"m03-{uuid.uuid4().hex[:8]}", uuid.uuid4().hex + uuid.uuid4().hex[:8]
    with DockerLab() as lab:
        try:
            tags = build_targets(lab, root, {"APP_VERSION": version, "GIT_COMMIT": revision})
            facts = {target: probe(lab, f"probe-{target}", tag) for target, tag in tags.items()}
        except pytest.fail.Exception as error:
            yield Built(error=str(error))
            return
        yield Built(lab, root, tags, version, revision, facts)


@pytest.fixture(scope="module")
def stack(built, project_root):
    if built.error:
        yield Stack(error=built.error)
        return
    compose = project_root / COMPOSE
    if not compose.is_file():
        yield Stack(error=missing(compose, DOC))
        return
    env = {"OLIST_API_IMAGE": built.tags["api"], "OLIST_WORKER_IMAGE": built.tags["worker"],
           "POSTGRES_PASSWORD": secrets.token_hex(12)}
    try:
        project = built.lab.compose(built.root / COMPOSE, env=env, timeout=180)
        url = f"http://127.0.0.1:{project.port('api', 8000)}"
    except pytest.fail.Exception as error:
        yield Stack(error=str(error))
        return
    except KeyError:
        yield Stack(error="Service api phải mở cổng container 8000 (xem mục 2 của đề)")
        return
    yield Stack(project, url)


def test_m03_dockerfile_rules(project_root):
    found = dockerfile_problems(require_file(project_root / DOCKERFILE).read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


@pytest.mark.parametrize("target", TARGETS)
def test_m03_image_policy(built, target):
    built.require()
    found = image_problems(built.lab, built.tags[target], target, built.version, built.revision, built.facts[target])
    assert not found, "\n".join(found)


def test_m03_images_share_dependencies(built):
    built.require()
    deps = {target: built.facts[target]["deps"] for target in TARGETS}
    for target, found in deps.items():
        assert len(found) == 1, (f"Image {target} phải có đúng một thư mục site-packages chứa redis-*.dist-info, "
                                 f"tìm thấy {found or 'không có'}")
    assert deps["api"] == deps["worker"], (
        "api và worker phải dùng chung một bộ dependency build một lần ở stage chung (cùng đường dẫn, cùng tệp), "
        f"không cài lại riêng cho từng target: {deps}")


def test_m03_compose_rules(project_root):
    path = require_file(project_root / COMPOSE)
    found = compose_problems(load_yaml(path), path.read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


def test_m03_stack_healthy(stack):
    stack.require()
    rows = {row.get("Service"): row for row in stack.project.ps()}
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and any(rows.get(s, {}).get("Health") != "healthy" for s in TARGETS):
        time.sleep(1)
        rows = {row.get("Service"): row for row in stack.project.ps()}
    states = {s: (rows.get(s, {}).get("State"), rows.get(s, {}).get("Health")) for s in TARGETS}
    assert all(state == ("running", "healthy") for state in states.values()), (
        f"api và worker phải running và healthy theo HEALTHCHECK của image, đang là {states}\n"
        f"{stack.project.logs(tail=20)[-3000:]}")


def test_m03_stack_serves_version_and_ready(stack, built):
    stack.require()
    health = httpx.get(stack.url + "/healthz", timeout=10)
    assert health.status_code == 200 and health.json().get("version") == built.version, (
        f"/healthz phải trả version = build arg APP_VERSION ({built.version}), nhận {health.status_code} {health.text}")
    ready = httpx.get(stack.url + "/readyz", timeout=10)
    assert ready.status_code == 200, f"/readyz phải 200 (DB và Redis sẵn sàng), nhận {ready.status_code} {ready.text}"


def test_m03_worker_processes_job(stack):
    stack.require()
    response = httpx.post(stack.url + "/jobs/recompute", timeout=10)
    assert response.status_code == 202, f"POST /jobs/recompute phải 202, nhận {response.status_code} {response.text}"
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        for line in stack.project.logs("worker").splitlines():
            if job_id in line and "job done" in line:
                return
        time.sleep(1)
    pytest.fail(f"Worker không xử lý job {job_id} trong 30 giây:\n{stack.project.logs('worker', tail=20)[-2000:]}")


def test_m03_worker_stops_cleanly(stack):
    stack.require()
    start = time.monotonic()
    result = stack.project.run("stop", "worker", timeout=120)
    waited = time.monotonic() - start
    assert result.returncode == 0, result.stderr
    row = next((r for r in stack.project.ps() if r.get("Service") == "worker"), {})
    assert row.get("ExitCode") == 0, (f"worker phải thoát 0 khi nhận SIGTERM (exec form, Python là PID 1), nhận mã "
                                      f"{row.get('ExitCode')} sau {waited:.1f} giây")


def test_m03_trivy_config(project_root):
    found = trivy_config_problems(load_yaml(require_file(project_root / "container" / "trivy.yaml")))
    ignore = project_root / "container" / ".trivyignore.yaml"
    found += ignore_problems(load_yaml(ignore)) if ignore.is_file() else [f"Thiếu {ignore.name} (trivy.yaml trỏ tới nó)"]
    assert not found, "\n".join(found)


@pytest.mark.parametrize("target", TARGETS)
def test_m03_sbom_lists_dependencies(built, target, tmp_path):
    built.require()
    require_trivy()
    code, sbom, stderr = trivy_image(built.tags[target], tmp_path, "--format", "cyclonedx")
    assert code == 0 and sbom, f"trivy image --format cyclonedx lỗi: {stderr[-800:]}"
    have = {(c.get("name", "").lower().replace("_", "-"), c.get("version")) for c in sbom.get("components") or []
            if str(c.get("purl", "")).startswith("pkg:pypi/")}
    lacking = [f"{name}=={version}" for name, version in pinned_requirements().items() if (name, version) not in have]
    assert not lacking, (f"SBOM của image {target} thiếu {lacking}: scanner phải thấy được gói Python (giữ *.dist-info "
                         "trong site-packages), nếu không mọi lần quét lỗ hổng đều mù")


@pytest.mark.parametrize("target", TARGETS)
def test_m03_no_secret_in_image(built, target, tmp_path):
    built.require()
    require_trivy()
    code, report, stderr = trivy_image(built.tags[target], tmp_path, "--scanners", "secret", "--format", "json")
    assert report, f"trivy quét secret lỗi (mã {code}): {stderr[-800:]}"
    assert not secret_findings(report), f"Image {target} chứa bí mật: {secret_findings(report)}"


def policy_repo(project_root: Path, work: Path, extra: list[dict] | None = None) -> tuple[Path, list]:
    """Bản chép gốc repo chỉ gồm container/trivy.yaml và container/.trivyignore.yaml (bỏ expired_at, cộng `extra`), để
    trivy chạy từ gốc repo như trivy-action trong CI."""
    (work / "container").mkdir(parents=True)
    shutil.copyfile(project_root / "container" / "trivy.yaml", work / "container" / "trivy.yaml")
    ignore = project_root / IGNOREFILE
    data = without_expiry(load_yaml(ignore)) if ignore.is_file() else {}
    data["vulnerabilities"] = list(data.get("vulnerabilities") or []) + list(extra or [])
    (work / IGNOREFILE).write_text(yaml.safe_dump(data), encoding="utf-8")
    return work / "container" / "trivy.yaml", data["vulnerabilities"]


@pytest.mark.parametrize("target", TARGETS)
def test_m03_gate_follows_policy(built, project_root, target, tmp_path):
    built.require()
    require_file(project_root / "container" / "trivy.yaml")
    require_trivy_db(tmp_path)
    config, entries = policy_repo(project_root, tmp_path / "policy")
    code, gated, stderr = trivy_image(built.tags[target], tmp_path, "--scanners", "vuln", "--format", "json",
                                      config=config, cwd=config.parent.parent)
    assert gated, f"trivy với trivy.yaml của bạn không chạy được (mã {code}): {stderr[-800:]}"
    _, control, _ = trivy_image(built.tags[target], tmp_path, "--scanners", "vuln", "--format", "json")
    reported = findings(gated)
    found = [f"{v['VulnerabilityID']} ({v.get('PkgName')}, {v.get('Severity')}, {v.get('Status')}) bị báo dù chính sách chỉ "
             "chặn HIGH/CRITICAL đã có bản vá" for v in reported
             if v.get("Severity") not in BLOCKING or v.get("Status") != "fixed"]
    shown_ids = {(v["VulnerabilityID"], v.get("PkgName")) for v in reported}
    hidden = [f"{v['VulnerabilityID']} ({v.get('PkgName')})" for v in findings(control)
              if v.get("Severity") in BLOCKING and v.get("Status") == "fixed" and not purl_ignored(v, entries)
              and (v["VulnerabilityID"], v.get("PkgName")) not in shown_ids]
    if hidden:
        found.append(f"Gate che mất lỗ hổng chặn không có trong ngoại lệ: {hidden}")
    if (code != 0) != bool(reported):
        found.append(f"Mã thoát {code} không khớp kết quả: {len(reported)} lỗ hổng chặn (có lỗ hổng chặn thì phải khác 0, "
                     "không có thì 0)")
    assert not found, "\n".join(found)


def test_m03_ignorefile_applies_from_repo_root(built, project_root, tmp_path):
    """Ngoại lệ trong container/.trivyignore.yaml phải có hiệu lực khi trivy chạy từ gốc repo với
    --config container/trivy.yaml, đúng như trivy-action trong CI M04."""
    built.require()
    require_file(project_root / "container" / "trivy.yaml")
    require_trivy_db(tmp_path)
    _, control, _ = trivy_image(built.tags["api"], tmp_path, "--scanners", "vuln", "--format", "json")
    sample = next((v for v in findings(control) if (v.get("PkgIdentifier") or {}).get("PURL")), None)
    if sample is None:
        pytest.skip("DB trivy hiện tại không còn lỗ hổng nào trong image api để thử ngoại lệ")
    probe_entry = {"id": sample["VulnerabilityID"], "purls": [sample["PkgIdentifier"]["PURL"]],
                   "statement": "Mục thử của test: kiểm ngoại lệ được đọc khi trivy chạy từ gốc repo."}
    config, _ = policy_repo(project_root, tmp_path / "policy", [probe_entry])
    _, report, stderr = trivy_image(built.tags["api"], tmp_path, "--scanners", "vuln", "--format", "json",
                                    "--severity", "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL", "--ignore-unfixed=false",
                                    "--exit-code", "0", config=config, cwd=config.parent.parent)
    assert report, f"trivy với trivy.yaml của bạn không chạy được: {stderr[-800:]}"
    pair = (sample["VulnerabilityID"], sample.get("PkgName"))
    assert pair not in {(v["VulnerabilityID"], v.get("PkgName")) for v in findings(report)}, (
        f"Chạy từ gốc repo với --config container/trivy.yaml, ngoại lệ {pair[0]} trong {IGNOREFILE} không có hiệu lực: "
        "ignorefile phải trỏ đúng tệp tính từ gốc repo")


def test_m03_postgres_data_path_rule():
    def problems(target: str) -> list[str]:
        data = {"services": {name: {} for name in ("api", "worker", "redis")}}
        data["services"]["postgres"] = {"volumes": [f"pgdata:{target}"]}
        return [p for p in compose_problems(data, "") if "named volume" in p]

    assert not problems("/var/lib/postgresql/data")
    assert not problems("/var/lib/postgresql")
    assert problems("/srv/pgdata")


def test_m03_probe_finds_venv_off_path(tmp_path):
    """fixtures/venv-off-path: venv không nằm trong PATH, CMD gọi /opt/venv/bin/... trực tiếp; phép kiểm dependency
    dùng chung vẫn phải tìm thấy site-packages qua redis-*.dist-info."""
    Exercise.require_tool("docker")
    root = assemble(tmp_path / "repo", tmp_path / "none", extra={DOCKERFILE: FIXTURES / "venv-off-path" / "Dockerfile"})
    with DockerLab() as lab:
        tags = build_targets(lab, root, {}, prefix="offpath-")
        deps = {target: probe(lab, f"probe-offpath-{target}", tag)["deps"] for target, tag in tags.items()}
    assert len(deps["api"]) == 1 and deps["api"] == deps["worker"], deps
    assert deps["api"][0].startswith("/opt/venv/"), deps


def test_m03_checks_catch_defective(tmp_path):
    """fixtures/defective/container: một stage, root, CMD dạng shell, không HEALTHCHECK, không nhãn OCI, `COPY . .` kéo
    theo .env và test; compose build tại chỗ, mở cổng Postgres, mật khẩu dạng chữ, image không ghim."""
    defective = DEFECTIVE / "container"
    assert len(dockerfile_problems((defective / "Dockerfile").read_text(encoding="utf-8"))) >= 2
    assert any("chưa ghim" in p for p in dockerfile_problems("FROM python:3.12-slim AS api\nFROM api AS worker\n"))
    compose = "\n".join(compose_problems(load_yaml(defective / "compose.yaml"), (defective / "compose.yaml").read_text()))
    for needle in ("OLIST_API_IMAGE", "không build", "read_only", "cap_drop", "service_healthy", "chưa ghim",
                   "POSTGRES_PASSWORD", "không mở cổng", "max-size", "mật khẩu dạng chữ", "stop_grace_period"):
        assert needle in compose, compose
    trivy = "\n".join(trivy_config_problems(load_yaml(defective / "trivy.yaml")))
    for needle in ("severity", "exit-code", "ignore-unfixed", "secret"):
        assert needle in trivy, trivy
    Exercise.require_tool("docker")
    root = assemble(tmp_path / "repo", tmp_path / "none", extra={DOCKERFILE: defective / "Dockerfile"})
    with DockerLab() as lab:
        tag = lab.build(root, "bad", dockerfile=DOCKERFILE, target="api", build_args={"APP_VERSION": "x"})
        facts = probe(lab, "probe-bad", tag)
        found = "\n".join(image_problems(lab, tag, "api", "x", "y", facts))
        for needle in ("UID số", "UID 0", "dạng shell", "HEALTHCHECK", "org.opencontainers.image.revision", ".env"):
            assert needle in found, found
        require_trivy()
        _, report, stderr = trivy_image(tag, tmp_path, "--scanners", "secret", "--format", "json")
        assert any("github" in s.lower() for s in secret_findings(report)), (
            f"trivy phải thấy token giả {FAKE_TOKEN[:8]}... trong image lỗi: {secret_findings(report)} {stderr[-400:]}")
