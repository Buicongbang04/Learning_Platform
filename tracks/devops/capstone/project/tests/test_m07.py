"""M07: repo GitOps của Olist Shop (chart M06 cộng `gitops/`) do ArgoCD đồng bộ vào namespace của lab, Secret DB mã hoá bằng
SOPS, đổi version trong git thì rollout, revert thì quay lại. Hợp đồng đầy đủ ở capstone/milestones/m07-gitops-secrets.md."""

import base64
import hmac
import json
import re
import secrets
import shutil
import time
from pathlib import Path

import pytest
import yaml

from olist_stack import missing
from test_m06 import DEPS, call, chart_path, get_json, helm_offline, restricted_gaps
from testkit import (AGE_MIN_VERSION, HELM_MIN_VERSION, KUBE_ARGOCD_CMP, KUBE_GATEWAY_SERVICE, KUBE_IMAGES, KUBE_IN_CLUSTER,
                     SOPS_MIN_VERSION, Exercise, KubeLab, age_keypair, run_sandboxed, sops_env)

DOC = "m07-gitops-secrets.md"
APP = "olist-shop"
RELEASE = "shop"
API, WORKER = f"{RELEASE}-api", f"{RELEASE}-worker"
GITOPS = "gitops"
CHART_PATH = "chart/olist-shop"
SECRETS_PATH = "gitops/secrets"
VALUES = "values-lab.yaml"
VALUES_PATH = f"{GITOPS}/{VALUES}"
SEAL = "seal-db.sh"
TARGET = "secrets/olist-db.enc.yaml"
FILES = ("application.yaml", VALUES, ".sops.yaml", SEAL, "secrets/kustomization.yaml")
SECRET_FILES = {"kustomization.yaml", "olist-db.enc.yaml"}
SECRET_KEYS = {"POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD", "DATABASE_URL"}
CURRENT, NEXT = "1.0", "1.1"
NEXT_IMAGE = f"devops-track/olist-shop:{NEXT}"
NEXT_TAG = f"docker tag {KUBE_IMAGES['olist']} {NEXT_IMAGE}"
ENCRYPTED = re.compile(r"^ENC\[AES256_GCM,data:.+,type:\w+\]$")
FORBIDDEN_SOPS = ("kms", "gcp_kms", "azure_kv", "hc_vault_transit_uri", "hc_vault", "pgp", "key_groups")
SYNC_WAIT = 300
VERSION_WAIT = 90


def database_url(password: str) -> str:
    return f"postgresql+psycopg://olist:{password}@postgres:5432/olist"


def same(a, b) -> bool:
    """So hai giá trị bí mật ngoài câu assert, để pytest không in chúng khi lệch."""
    return isinstance(a, str) and isinstance(b, str) and hmac.compare_digest(a.encode(), b.encode())


def needles(password: str) -> list[bytes]:
    url = database_url(password)
    return [password.encode(), base64.b64encode(password.encode()), base64.b64encode(url.encode())]


def leaked_files(root: Path, password: str) -> list[str]:
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            if any(n in data for n in needles(password)) or b"AGE-SECRET-KEY-" in data:
                found.append(str(path.relative_to(root)))
    return found


def gitops_dir(project_root: Path) -> Path:
    return project_root / GITOPS


def missing_files(project_root: Path) -> list[str]:
    found = [missing(gitops_dir(project_root) / name, DOC) for name in FILES if not (gitops_dir(project_root) / name).is_file()]
    chart = chart_path(project_root) / "Chart.yaml"
    if not chart.is_file():
        found.append(missing(chart, "m06-kubernetes-helm.md") + " (M07 dùng lại chart của M06)")
    return found


def require_files(project_root: Path) -> Path:
    found = missing_files(project_root)
    if found:
        pytest.fail("\n".join(found), pytrace=False)
    return gitops_dir(project_root)


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}", pytrace=False)


def application_problems(project_root: Path) -> list[str]:
    try:
        docs = [d for d in yaml.safe_load_all((gitops_dir(project_root) / "application.yaml").read_text(encoding="utf-8")) if d]
    except yaml.YAMLError as error:
        return [f"application.yaml không phải YAML hợp lệ: {error}"]
    if len(docs) != 1 or not isinstance(docs[0], dict) or docs[0].get("kind") != "Application":
        return ["application.yaml chứa đúng một object kind Application"]
    app = docs[0]
    spec = app.get("spec") or {}
    found = []
    if app.get("apiVersion") != "argoproj.io/v1alpha1" or (app.get("metadata") or {}).get("name") != APP:
        found.append(f"Application apiVersion argoproj.io/v1alpha1, tên {APP}")
    if "namespace" in (app.get("metadata") or {}):
        found.append("Không ghi metadata.namespace: test tạo Application trong namespace của lab")
    if spec.get("project") != "LAB_PROJECT":
        found.append("spec.project là placeholder LAB_PROJECT (project riêng của lab)")
    if spec.get("destination") != {"server": KUBE_IN_CLUSTER, "namespace": "LAB_NAMESPACE"}:
        found.append(f"spec.destination đúng {{server: {KUBE_IN_CLUSTER}, namespace: LAB_NAMESPACE}}: {spec.get('destination')}")
    if "source" in spec or not isinstance(spec.get("sources"), list):
        found.append("Dùng spec.sources (nhiều nguồn: chart Helm và thư mục Secret SOPS), không dùng spec.source")
        return found
    sources = [s for s in spec["sources"] if isinstance(s, dict)]
    if len(sources) != len(spec["sources"]):
        found.append("Mỗi phần tử của spec.sources là một mapping")
    for source in sources:
        if source.get("repoURL") != "LAB_REPO_URL" or source.get("targetRevision") != "main":
            found.append(f"Mọi nguồn có repoURL LAB_REPO_URL và targetRevision main: {source.get('repoURL')} "
                         f"{source.get('targetRevision')}")
    rendered = [s for s in sources if "path" in s]
    helm = [s for s in rendered if s.get("path") == CHART_PATH]
    sealed = [s for s in rendered if s.get("path") == SECRETS_PATH]
    others = sorted(str(s.get("path")) for s in rendered if s.get("path") not in (CHART_PATH, SECRETS_PATH))
    if others:
        found.append(f"Chỉ hai nguồn có path: {CHART_PATH} và {SECRETS_PATH} (thêm nguồn chỉ có ref được), đang có thêm {others}")
    if len(helm) != 1:
        found.append(f"Cần đúng một nguồn path {CHART_PATH} (chart M06, ArgoCD render bằng Helm)")
    else:
        chart = helm[0]
        options = chart.get("helm") or {}
        if "plugin" in chart or "kustomize" in chart or "directory" in chart:
            found.append(f"Nguồn {CHART_PATH} render bằng Helm có sẵn của ArgoCD (khoá helm), không plugin, kustomize, directory")
        if options.get("releaseName") != RELEASE:
            found.append(f"helm.releaseName là {RELEASE} (tên object shop-api, shop-worker như M06)")
        files = [str(f) for f in options.get("valueFiles") or []]
        if not any(f == VALUES_PATH or f.endswith("/" + VALUES_PATH) for f in files):
            found.append(f"helm.valueFiles phải đọc {VALUES_PATH} trong repo (version nằm trong git): {files}")
        if any(p.get("name") in ("image.tag", "image") for p in options.get("parameters") or [] if isinstance(p, dict)):
            found.append("Không đặt image.tag trong Application: version chỉ nằm trong gitops/values-lab.yaml")
        if "image" in (options.get("valuesObject") or {}) or "image" in str(options.get("values") or ""):
            found.append("Không đặt image trong valuesObject/values của Application: version chỉ nằm trong gitops/values-lab.yaml")
    if len(sealed) != 1:
        found.append(f"Cần đúng một nguồn path {SECRETS_PATH} cho Secret mã hoá")
    elif (sealed[0].get("plugin") or {}).get("name") != KUBE_ARGOCD_CMP:
        found.append(f"Nguồn {SECRETS_PATH} dùng plugin {KUBE_ARGOCD_CMP} (chỉ plugin này có khoá age để giải mã)")
    automated = (spec.get("syncPolicy") or {}).get("automated")
    if not isinstance(automated, dict) or automated.get("prune") is not True or automated.get("selfHeal") is not True:
        found.append("syncPolicy.automated bật prune: true và selfHeal: true")
    for key in ("operation", "status"):
        if key in app:
            found.append(f"Không ghi {key} trong manifest")
    return found


def values_of(gitops: Path) -> dict:
    data = load_yaml(gitops / VALUES)
    return data if isinstance(data, dict) else {}


def bumped(text: str, tag: str) -> str:
    data = yaml.safe_load(text) or {}
    data.setdefault("image", {})["tag"] = tag
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def render(chart: Path, home: Path, values_text: str, host: str = "shop.olist.test") -> tuple[int, list[dict], str]:
    home.mkdir(parents=True, exist_ok=True)
    values = home / VALUES
    values.write_text(values_text, encoding="utf-8")
    result = helm_offline(chart, home, "template", RELEASE, str(chart), "-f", str(values), "--set", f"route.host={host}")
    if result.returncode != 0:
        return result.returncode, [], result.stderr[-1500:]
    return 0, [d for d in yaml.safe_load_all(result.stdout) if d], ""


def deployment_images(docs: list[dict]) -> dict:
    return {d["metadata"]["name"]: [c.get("image") for c in d["spec"]["template"]["spec"].get("containers") or []]
            for d in docs if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") in (API, WORKER)}


def sops_rule_problems(gitops: Path) -> list[str]:
    config = load_yaml(gitops / ".sops.yaml") or {}
    rules = config.get("creation_rules") if isinstance(config, dict) else None
    matching = [r for r in rules or [] if isinstance(r, dict) and re.search(str(r.get("path_regex", "$^")), TARGET)]
    if not matching:
        return [f".sops.yaml cần creation_rule có path_regex khớp {TARGET} (đường dẫn tính từ thư mục gitops/)"]
    rule, found = matching[0], []
    raw = rule.get("age", "")
    recipients = sorted(r.strip() for item in (raw if isinstance(raw, list) else [raw]) for r in str(item).split(",") if r.strip())
    if recipients != ["ARGOCD_AGE_RECIPIENT", "TEAM_AGE_RECIPIENT"]:
        found.append(f"Rule mã hoá cho đúng hai recipient TEAM_AGE_RECIPIENT và ARGOCD_AGE_RECIPIENT (test thay bằng khoá thật): "
                     f"{recipients}")
    pattern = rule.get("encrypted_regex")
    if not pattern:
        found.append("Chỉ mã hoá trường dữ liệu (encrypted_regex), metadata còn đọc được khi review")
    else:
        found += [f"encrypted_regex phải khớp {k}" for k in ("data", "stringData") if not re.search(pattern, k)]
        found += [f"encrypted_regex không được khớp {k}" for k in ("apiVersion", "kind", "metadata", "name", "type")
                  if re.search(pattern, k)]
    if any(k in rule for k in FORBIDDEN_SOPS):
        found.append("Chỉ dùng age (sidecar của ArgoCD từ chối tệp có khoá KMS, Vault, PGP)")
    return found


def secret_dir_problems(gitops: Path) -> list[str]:
    found = []
    kustomization = load_yaml(gitops / "secrets" / "kustomization.yaml") or {}
    if not isinstance(kustomization, dict) or "olist-db.enc.yaml" not in (kustomization.get("resources") or []):
        found.append("secrets/kustomization.yaml liệt kê olist-db.enc.yaml trong resources")
    elif any(kustomization.get(k) for k in ("secretGenerator", "configMapGenerator", "helmCharts", "components", "generators")):
        found.append("secrets/kustomization.yaml chỉ liệt kê olist-db.enc.yaml, không generator, helmCharts hay components")
    extra = sorted(p.name for p in (gitops / "secrets").iterdir() if p.name not in SECRET_FILES)
    if extra:
        found.append(f"secrets/ chỉ có kustomization.yaml và olist-db.enc.yaml (do seal-db.sh ghi), đang có thêm {extra}")
    for path in sorted(gitops.rglob("*.y*ml")):
        try:
            docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(d, dict)]
        except yaml.YAMLError:
            continue
        for doc in docs:
            values = {**(doc.get("data") or {}), **(doc.get("stringData") or {})} if doc.get("kind") == "Secret" else {}
            if any(not ENCRYPTED.match(str(v)) for v in values.values()):
                found.append(f"{path.relative_to(gitops)}: Secret có giá trị chưa mã hoá (không in giá trị)")
    return found


def stage(dest: Path, project_root: Path, team: str, argocd: str) -> Path:
    """Repo GitOps khi chấm: `chart/olist-shop/` (chart M06) và `gitops/` của bạn, recipient thật thay placeholder trong
    `.sops.yaml`, bỏ `olist-db.enc.yaml` cũ (mã hoá cho khoá khác) để seal-db.sh ghi lại."""
    shutil.copytree(chart_path(project_root), dest / CHART_PATH, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(gitops_dir(project_root), dest / GITOPS, ignore=shutil.ignore_patterns("__pycache__"))
    config = dest / GITOPS / ".sops.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("TEAM_AGE_RECIPIENT", team)
                      .replace("ARGOCD_AGE_RECIPIENT", argocd), encoding="utf-8")
    (dest / GITOPS / TARGET).unlink(missing_ok=True)
    return dest


def seal(tmp: Path, gitops: Path, key: Path, password: str, project_root: Path):
    home = tmp / "seal-home"
    return run_sandboxed(["bash", SEAL], writable=[gitops, home], cwd=gitops, env=sops_env(home, key, outside=[project_root]),
                         readonly=[key.parent], input=password + "\n", timeout=60)


def decrypt(tmp: Path, gitops: Path, key: Path, project_root: Path) -> tuple[int, dict]:
    home = tmp / f"decrypt-{key.parent.name}"
    result = run_sandboxed(["sops", "decrypt", TARGET], writable=[home], cwd=gitops, readonly=[key.parent, gitops],
                           env=sops_env(home, key, outside=[project_root]), timeout=60)
    if result.returncode != 0:
        return result.returncode, {}
    data = yaml.safe_load(result.stdout)
    return 0, data if isinstance(data, dict) else {}


def sealed_problems(state: dict) -> list[str]:
    """Kiểm kết quả của seal-db.sh; không bao giờ đưa giá trị bí mật vào thông báo."""
    result, gitops, password = state["result"], state["gitops"], state["password"]
    output = (result.stdout + result.stderr).encode()
    if any(n in output for n in needles(password)):
        return ["seal-db.sh in mật khẩu (hay base64 của nó) ra stdout/stderr (không in giá trị)"]
    if result.returncode != 0:
        return [f"seal-db.sh lỗi (mã {result.returncode}): {result.stderr.strip()[-800:]}"]
    if not (gitops / TARGET).is_file():
        return [f"seal-db.sh phải ghi gitops/{TARGET}"]
    leaked = leaked_files(state["repo"], password)
    if leaked:
        return [f"Giá trị rõ (hay base64 của nó) nằm trong repo: {leaked} (không in giá trị)"]
    doc = yaml.safe_load((gitops / TARGET).read_text(encoding="utf-8")) or {}
    found = []
    if doc.get("kind") != "Secret" or (doc.get("metadata") or {}).get("name") != "olist-db":
        found.append("kind Secret và metadata.name olist-db còn đọc được (chỉ mã hoá trường dữ liệu)")
    values = {**(doc.get("data") or {}), **(doc.get("stringData") or {})}
    if set(values) != SECRET_KEYS:
        found.append(f"Secret olist-db có đúng các khoá {sorted(SECRET_KEYS)}, đang có {sorted(values)}")
    if not values or not all(ENCRYPTED.match(str(v)) for v in values.values()):
        found.append("Mọi giá trị trong stringData/data phải là ENC[...]")
    recipients = sorted(e.get("recipient") for e in (doc.get("sops") or {}).get("age") or [])
    if recipients != sorted(state["recipients"]):
        found.append("Tệp phải mã hoá cho đúng hai recipient của .sops.yaml (team và ArgoCD)")
    return found


def decoded(doc: dict) -> dict:
    out = {k: str(v) for k, v in (doc.get("stringData") or {}).items()}
    for key, value in (doc.get("data") or {}).items():
        try:
            out[key] = base64.b64decode(str(value)).decode()
        except ValueError:
            out[key] = ""
    return out


def secret_matches(values: dict, password: str) -> list[str]:
    expected = {"POSTGRES_USER": "olist", "POSTGRES_DB": "olist", "POSTGRES_PASSWORD": password,
                "DATABASE_URL": database_url(password)}
    return [key for key, want in expected.items() if not same(values.get(key), want)]


def seal_with_keys(tmp: Path, project_root: Path, argocd: tuple[Path | None, str]) -> dict:
    Exercise.require_tool("sops", SOPS_MIN_VERSION)
    team_key, team = age_keypair(tmp / "team", outside=[project_root])
    repo = stage(tmp / "repo", project_root, team, argocd[1])
    password = secrets.token_urlsafe(18)
    result = seal(tmp, repo / GITOPS, team_key, password, project_root)
    return {"repo": repo, "gitops": repo / GITOPS, "password": password, "result": result, "team_key": team_key,
            "recipients": [team, argocd[1]], "argocd_key": argocd[0]}


def test_m07_application_manifest(project_root):
    require_files(project_root)
    found = application_problems(project_root)
    assert not found, "\n".join(found)


def test_m07_values_drive_version(project_root, tmp_path):
    gitops = require_files(project_root)
    tag = (values_of(gitops).get("image") or {}).get("tag")
    assert tag == CURRENT, f"{VALUES_PATH}: image.tag là chuỗi \"{CURRENT}\" (version đang chạy nằm trong git), đang là {tag!r}"
    text = (gitops / VALUES).read_text(encoding="utf-8")
    chart = chart_path(project_root)
    code, docs, error = render(chart, tmp_path / "now", text)
    assert code == 0, f"helm template chart M06 với {VALUES_PATH} lỗi:\n{error}"
    images = deployment_images(docs)
    assert images == {API: [KUBE_IMAGES["olist"]], WORKER: [KUBE_IMAGES["olist"]]}, (
        f"Chart cộng {VALUES_PATH} phải chạy {KUBE_IMAGES['olist']} cho {API}, {WORKER}: {images}")
    assert not [d for d in docs if d.get("kind") == "Secret"], "Chart không tạo Secret: olist-db đến từ nguồn SOPS"
    code, docs, error = render(chart, tmp_path / "next", bumped(text, NEXT))
    assert code == 0, f"helm template với image.tag {NEXT} lỗi:\n{error}"
    images = deployment_images(docs)
    assert images == {API: [NEXT_IMAGE], WORKER: [NEXT_IMAGE]}, f"Đổi image.tag thành {NEXT} phải đổi image của cả hai: {images}"


def test_m07_sops_config_and_secret_dir(project_root):
    gitops = require_files(project_root)
    found = sops_rule_problems(gitops) + secret_dir_problems(gitops)
    keys = [str(p.relative_to(project_root)) for part in (GITOPS, "chart") for p in sorted((project_root / part).rglob("*"))
            if p.is_file() and b"AGE-SECRET-KEY-" in p.read_bytes()]
    if keys:
        found.append(f"Khoá riêng age nằm trong project: {keys}")
    assert not found, "\n".join(found)


def test_m07_seal_db_encrypts_for_team_and_argocd(project_root, tmp_path):
    require_files(project_root)
    Exercise.require_tool("age-keygen", AGE_MIN_VERSION)
    argocd_key, argocd = age_keypair(tmp_path / "argocd", outside=[project_root])
    state = seal_with_keys(tmp_path, project_root, (argocd_key, argocd))
    found = sealed_problems(state)
    assert not found, "\n".join(found)
    for who, key in (("team", state["team_key"]), ("ArgoCD", argocd_key)):
        code, doc = decrypt(tmp_path, state["gitops"], key, project_root)
        assert code == 0, f"Khoá của {who} không giải mã được gitops/{TARGET}"
        wrong = secret_matches(decoded(doc), state["password"])
        assert not wrong, f"Giải mã bằng khoá của {who}: khoá {wrong} sai giá trị mong đợi (không in giá trị)"


class Deployed:
    def __init__(self) -> None:
        self.lab: KubeLab | None = None
        self.error = ""
        self.failure = ""
        self.password = ""
        self.revisions: list[str] = []
        self.steps: dict[str, dict] = {}

    def step(self, name: str) -> tuple[KubeLab, dict]:
        if self.error:
            pytest.fail(self.error, pytrace=False)
        if name not in self.steps:
            pytest.fail(f"Chưa tới bước {name}: {self.failure or 'bước trước lỗi'}", pytrace=False)
        return self.lab, self.steps[name]


def version_of(answer: str) -> str | None:
    try:
        body = json.loads(answer.split(" ", 2)[2])
    except (IndexError, ValueError):
        return None
    return body.get("version") if isinstance(body, dict) else None


def served_versions(lab: KubeLab, want: str) -> list[str]:
    """Gọi `/healthz` qua Gateway 6 lần mỗi vòng tới khi mọi lần trả `version` `want` (tối đa `VERSION_WAIT` giây); trả kết
    quả của vòng cuối (version, hoặc câu trả lời khi không đọc được version)."""
    targets = [f"GET {KUBE_GATEWAY_SERVICE}/healthz?n={i}|{lab.hostname}" for i in range(6)]
    deadline = time.monotonic() + VERSION_WAIT
    seen: list[str] = []
    while True:
        answers = call(lab, "probe", *targets)
        seen = [version_of(answers[t]) or answers[t][:80] for t in targets]
        if set(seen) == {want} or time.monotonic() > deadline:
            return seen
        time.sleep(3)


def active_replicasets(lab: KubeLab, component: str) -> list[str]:
    items = (get_json(lab, "replicasets", "-l", f"app.kubernetes.io/instance={RELEASE},app.kubernetes.io/component={component}")
             or {}).get("items", [])
    return sorted(rs["metadata"]["name"] for rs in items if (rs.get("status") or {}).get("replicas"))


def observe(lab: KubeLab, want: str, status: dict) -> dict:
    deployments = {name: get_json(lab, "deployment", name) or {} for name in (API, WORKER)}
    ready = call(lab, "probe", f"GET {KUBE_GATEWAY_SERVICE}/readyz|{lab.hostname}")
    return {
        "status": status,
        "uid": {name: (d.get("metadata") or {}).get("uid") for name, d in deployments.items()},
        "images": {name: [c.get("image") for c in (((d.get("spec") or {}).get("template") or {}).get("spec") or {})
                          .get("containers") or []] for name, d in deployments.items()},
        "versions": served_versions(lab, want),
        "ready": list(ready.values())[0],
        "rs": active_replicasets(lab, "api"),
    }


def push_and_wait(lab: KubeLab, state: Deployed, repo: Path, want: str) -> dict:
    lab.gitops_repo(repo)
    state.revisions.append(lab.gitops_revision)
    status = lab.argocd_wait(APP, timeout=SYNC_WAIT)
    return observe(lab, want, status)


def deploy_problems(project_root: Path, tmp: Path) -> list[str]:
    found = missing_files(project_root)
    if found:
        return found
    found = application_problems(project_root)
    try:
        tag = (values_of(gitops_dir(project_root)).get("image") or {}).get("tag")
    except pytest.fail.Exception as error:
        return found + [str(error)]
    if tag != CURRENT:
        found.append(f"{VALUES_PATH}: image.tag phải là \"{CURRENT}\"")
    if found:
        return found
    Exercise.require_tool("helm", HELM_MIN_VERSION)
    code, docs, error = render(chart_path(project_root), tmp / "render",
                               (gitops_dir(project_root) / VALUES).read_text(encoding="utf-8"))
    return [f"helm template lỗi: {error}"] if code else restricted_gaps(docs)


def require_next_image() -> None:
    try:
        Exercise.require_kind_images(NEXT_IMAGE)
    except pytest.skip.Exception as error:
        pytest.skip(f"{error} Tag {NEXT} là bản giả lập của 'bản mới' trong lab, tạo trước khi nạp: {NEXT_TAG}")


@pytest.fixture(scope="module")
def deployed(project_root, tmp_path_factory):
    state = Deployed()
    tmp = tmp_path_factory.mktemp("m07")
    problems = deploy_problems(project_root, tmp)
    if problems:
        state.error = "Không deploy (khỏi chờ hết giờ): repo GitOps chưa đạt phần đọc tĩnh:\n" + "\n".join(problems)
        yield state
        return
    Exercise.require_tool("sops", SOPS_MIN_VERSION)
    Exercise.require_tool("age-keygen", AGE_MIN_VERSION)
    Exercise.require_cluster()
    Exercise.require_argocd()
    Exercise.require_gateway()
    Exercise.require_metrics()
    Exercise.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    require_next_image()
    with KubeLab(pod_security="restricted") as lab:
        state.lab = lab
        try:
            project = lab.argocd_project()
            sealed = seal_with_keys(tmp, project_root, (None, lab.sops_age_recipient))
            state.password = sealed["password"]
            found = sealed_problems(sealed)
            if found:
                pytest.fail("Không đẩy repo lên git server: " + "\n".join(found), pytrace=False)
            repo = sealed["repo"]
            deps = tmp / "deps.yaml"
            docs = [d for d in yaml.safe_load_all(DEPS.read_text(encoding="utf-8")) if d and d.get("kind") != "Secret"]
            deps.write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")
            lab.apply_learner(deps)
            for target in ("deployment/redis", "deployment/probe"):
                lab.kubectl("rollout", "status", target, "--timeout=180s", timeout=200)
            lab.gitops_repo(repo)
            state.revisions.append(lab.gitops_revision)
            text = (gitops_dir(project_root) / "application.yaml").read_text(encoding="utf-8")
            for placeholder, value in (("LAB_PROJECT", project), ("LAB_REPO_URL", lab.repo_url), ("LAB_NAMESPACE", lab.namespace)):
                text = text.replace(placeholder, value)
            manifest = tmp / "application.yaml"
            manifest.write_text(text, encoding="utf-8")
            lab.apply_learner(manifest)
            state.steps["initial"] = observe(lab, CURRENT, lab.argocd_wait(APP, timeout=SYNC_WAIT))
            values = repo / VALUES_PATH
            original = values.read_bytes()
            values.write_text(bumped(original.decode("utf-8"), NEXT), encoding="utf-8")
            state.steps["bump"] = push_and_wait(lab, state, repo, NEXT)
            values.write_bytes(original)
            state.steps["revert"] = push_and_wait(lab, state, repo, CURRENT)
        except (pytest.fail.Exception, AssertionError) as error:
            state.failure = str(error)
        yield state


def test_m07_argocd_syncs_chart_and_secret(deployed):
    lab, step = deployed.step("initial")
    resources = {(r.get("kind"), r.get("name")) for r in step["status"].get("resources") or []}
    wanted = {("Secret", "olist-db"), ("Deployment", API), ("Deployment", WORKER), ("HTTPRoute", API),
              ("HorizontalPodAutoscaler", API)}
    assert wanted <= resources, f"Application {APP} phải quản cả chart lẫn Secret, thiếu {sorted(wanted - resources)}"
    outside = sorted({r.get("namespace") for r in step["status"].get("resources") or []} - {lab.namespace, None, ""})
    assert not outside, f"Application chỉ quản object trong namespace của lab: {outside}"
    assert step["ready"].startswith("ok 200"), f"/readyz qua Gateway phải 200 (api đọc DATABASE_URL đã giải mã): {step['ready']}"
    assert set(step["versions"]) == {CURRENT}, f"/healthz qua Gateway phải trả version {CURRENT}: {step['versions']}"


def test_m07_secret_decrypted_by_argocd(deployed):
    lab, _ = deployed.step("initial")
    secret = get_json(lab, "secret", "olist-db") or {}
    annotations = (secret.get("metadata") or {}).get("annotations") or {}
    assert "argocd.argoproj.io/tracking-id" in annotations, "Secret olist-db phải do ArgoCD tạo từ nguồn SOPS"
    values = {k: base64.b64decode(v).decode() for k, v in (secret.get("data") or {}).items()}
    wrong = secret_matches(values, deployed.password)
    assert not wrong, f"Secret olist-db trên cluster: khoá {wrong} khác giá trị đã mã hoá (không in giá trị)"


def test_m07_secret_not_exposed(deployed):
    lab, _ = deployed.step("initial")
    app = lab.kubectl("get", "applications.argoproj.io", APP, "-o", "json").stdout
    described = lab.kubectl("describe", "applications.argoproj.io", APP).stdout
    encoded = [n.decode() for n in needles(deployed.password)]
    exposed = any(n in app or n in described for n in encoded)
    assert not exposed, "Giá trị Secret xuất hiện trong Application hay kubectl describe (không in giá trị)"


def test_m07_version_in_git_rolls_out(deployed):
    _, before = deployed.step("initial")
    _, step = deployed.step("bump")
    assert step["images"] == {API: [NEXT_IMAGE], WORKER: [NEXT_IMAGE]}, (
        f"Sau commit đổi image.tag thành {NEXT}, Deployment phải chạy {NEXT_IMAGE}: {step['images']}")
    assert set(step["versions"]) == {NEXT}, f"/healthz qua Gateway phải trả version {NEXT}: {step['versions']}"
    assert step["uid"] == before["uid"], "ArgoCD phải cập nhật Deployment tại chỗ (rolling update), không xoá rồi tạo lại"
    assert step["rs"] and step["rs"] != before["rs"], f"Đổi version phải tạo ReplicaSet mới: {before['rs']} -> {step['rs']}"


def test_m07_git_revert_rolls_back(deployed):
    _, first = deployed.step("initial")
    _, step = deployed.step("revert")
    assert step["images"] == {API: [KUBE_IMAGES["olist"]], WORKER: [KUBE_IMAGES["olist"]]}, (
        f"Sau commit revert, Deployment phải về {KUBE_IMAGES['olist']}: {step['images']}")
    assert set(step["versions"]) == {CURRENT}, f"/healthz qua Gateway phải trả lại version {CURRENT}: {step['versions']}"
    assert step["uid"] == first["uid"], "Revert vẫn là rolling update trên cùng Deployment"
    assert step["rs"] == first["rs"], (
        f"Revert render ra đúng pod template của commit đầu nên dùng lại ReplicaSet cũ: {first['rs']} -> {step['rs']} "
        "(giá trị đổi theo mỗi lần render, như randAlphaNum hay now, làm mỗi lần sync ra template mới)")
    history = [set(h.get("revisions") or [h.get("revision")]) for h in step["status"].get("history") or []]
    synced = [rev for rev in deployed.revisions if any(rev in item for item in history)]
    assert synced == deployed.revisions, (
        f"Lịch sử sync của Application phải có đủ ba commit (đầu, đổi version, revert): {len(synced)}/{len(deployed.revisions)}")


def test_m07_helpers_tolerate_bad_input(tmp_path):
    """Bộ kiểm tĩnh không vỡ với manifest hỏng và bộ quét rò rỉ bắt được cả dạng base64."""
    password = secrets.token_urlsafe(18)
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b64.yaml").write_text(f"x: {base64.b64encode(database_url(password).encode()).decode()}\n",
                                             encoding="utf-8")
    (tmp_path / "plain.txt").write_text(password, encoding="utf-8")
    (tmp_path / "ok.yaml").write_text("x: 1\n", encoding="utf-8")
    assert leaked_files(tmp_path, password) == ["a/b64.yaml", "plain.txt"]
    assert version_of('ok 200 {"status":"ok","version":"1.1"}') == "1.1"
    assert version_of("chan ConnectionRefusedError") is None and version_of("ok 200 <html>") is None
    assert yaml.safe_load(bumped("image:\n  repository: x\n", NEXT)) == {"image": {"repository": "x", "tag": NEXT}}
    assert secret_matches({"POSTGRES_USER": "olist"}, password) == ["POSTGRES_DB", "POSTGRES_PASSWORD", "DATABASE_URL"]
    project = tmp_path / "project"
    (project / GITOPS).mkdir(parents=True)
    (project / GITOPS / "application.yaml").write_text("kind: Application\nspec:\n  source: {}\n", encoding="utf-8")
    found = application_problems(project)
    assert any("spec.sources" in f for f in found) and any("LAB_PROJECT" in f for f in found), found
