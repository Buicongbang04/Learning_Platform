import base64
import hashlib
import json
import re
import secrets
import shutil

import pytest
import yaml

from testkit import (AGE_MIN_VERSION, KUBE_ARGOCD_CMP, KUBE_IMAGES, KUBECTL_MIN_VERSION, SOPS_MIN_VERSION, Exercise, KubeLab,
                     age_keypair, run_sandboxed, sops_env)

ex = Exercise(__file__)
APP = "olist-shop"
TARGET = "shop/olist-db.enc.yaml"
READYZ = ("import urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=5); "
          "print(r.status, r.read().decode())")
PASSWORD_HASH = 'printf %s "$POSTGRES_PASSWORD" | sha256sum'
ENCRYPTED = re.compile(r"^ENC\[AES256_GCM,data:.+,type:\w+\]$")


def require_tools() -> None:
    ex.require_tool("sops", SOPS_MIN_VERSION)
    ex.require_tool("age-keygen", AGE_MIN_VERSION)


def plain_secret(directory, password: str):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "olist-db.yaml"
    path.write_text(yaml.safe_dump({
        "apiVersion": "v1", "kind": "Secret", "metadata": {"name": "olist-db"}, "type": "Opaque",
        "stringData": {"POSTGRES_USER": "olist", "POSTGRES_DB": "olist", "POSTGRES_PASSWORD": password,
                       "DATABASE_URL": f"postgresql+psycopg://olist:{password}@postgres:5432/olist"}}, sort_keys=False),
        encoding="utf-8")
    return path


def needles(password: str) -> list[bytes]:
    url = f"postgresql+psycopg://olist:{password}@postgres:5432/olist"
    return [password.encode(), base64.b64encode(password.encode()), base64.b64encode(url.encode())]


def leaked_files(repo, password: str) -> list[str]:
    found = []
    for path in sorted(repo.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            if any(n in data for n in needles(password)) or b"AGE-SECRET-KEY-" in data:
                found.append(str(path.relative_to(repo)))
    return found


def stage(tmp, team: str, argocd: str):
    repo = tmp / "repo"
    shutil.copytree(ex.path("gitops"), repo)
    config = repo / ".sops.yaml"
    if config.is_file():
        text = config.read_text(encoding="utf-8").replace("TEAM_AGE_RECIPIENT", team).replace("ARGOCD_AGE_RECIPIENT", argocd)
        config.write_text(text, encoding="utf-8")
    return repo


def seal(tmp, repo, plain, key):
    home = tmp / "home"
    return run_sandboxed(["bash", str(ex.path("seal.sh")), str(plain), TARGET], writable=[repo, home], cwd=repo,
                         env=sops_env(home, key, outside=[ex.target]), readonly=[key.parent, plain.parent], timeout=60)


def decrypt(tmp, repo, key) -> tuple[int, dict]:
    home = tmp / f"home-{key.parent.name}"
    result = run_sandboxed(["sops", "decrypt", TARGET], writable=[home], cwd=repo, env=sops_env(home, key, outside=[ex.target]),
                           readonly=[key.parent, repo], timeout=60)
    return result.returncode, (yaml.safe_load(result.stdout) if result.returncode == 0 else {})


def sealed(tmp_path):
    require_tools()
    team_key, team = age_keypair(tmp_path / "team", outside=[ex.target])
    argo_key, argocd = age_keypair(tmp_path / "argocd", outside=[ex.target])
    password = secrets.token_urlsafe(18)
    plain = plain_secret(tmp_path / "plain", password)
    repo = stage(tmp_path, team, argocd)
    result = seal(tmp_path, repo, plain, team_key)
    return {"repo": repo, "result": result, "password": password, "team": (team_key, team), "argocd": (argo_key, argocd)}


def application() -> dict:
    docs = [d for d in yaml.safe_load_all(ex.read("application.yaml")) if d]
    assert len(docs) == 1 and docs[0].get("kind") == "Application", "application.yaml chứa đúng một Application"
    return docs[0]


def test_leak_scanner_catches_plaintext(tmp_path):
    password = secrets.token_urlsafe(18)
    (tmp_path / "shop").mkdir()
    plain_secret(tmp_path / "shop", password)
    (tmp_path / "shop" / "b64.yaml").write_text(f"data:\n  p: {base64.b64encode(password.encode()).decode()}\n", encoding="utf-8")
    assert leaked_files(tmp_path, password) == ["shop/b64.yaml", "shop/olist-db.yaml"]


def test_sops_config_rules():
    config = yaml.safe_load((ex.path("gitops") / ".sops.yaml").read_text(encoding="utf-8")) or {}
    rules = config.get("creation_rules") or []
    matching = [r for r in rules if re.search(r.get("path_regex", "$^"), TARGET)]
    assert matching, f"Cần creation_rule có path_regex khớp {TARGET}"
    rule = matching[0]
    recipients = [r.strip() for r in str(rule.get("age", "")).split(",")]
    assert sorted(recipients) == ["ARGOCD_AGE_RECIPIENT", "TEAM_AGE_RECIPIENT"], \
        f"Rule phải mã hoá cho cả team (TEAM_AGE_RECIPIENT) lẫn ArgoCD (ARGOCD_AGE_RECIPIENT), đang là {recipients}"
    pattern = rule.get("encrypted_regex")
    assert pattern, "Chỉ mã hoá trường dữ liệu của Secret (encrypted_regex), để metadata còn đọc được khi review"
    for key in ("data", "stringData"):
        assert re.search(pattern, key), f"encrypted_regex phải khớp {key}"
    for key in ("apiVersion", "kind", "metadata", "name", "type"):
        assert not re.search(pattern, key), f"encrypted_regex không được khớp {key}"
    assert not any(k in rule for k in ("kms", "gcp_kms", "azure_kv", "hc_vault_transit_uri", "pgp", "key_groups")), \
        "Bài chỉ dùng age (sidecar của ArgoCD từ chối tệp có khoá KMS, Vault, PGP)"


def test_seal_encrypts_fields_for_both_recipients(tmp_path):
    state = sealed(tmp_path)
    result, repo = state["result"], state["repo"]
    assert result.returncode == 0, f"seal.sh lỗi (mã {result.returncode}): {result.stderr.strip()[-800:]}"
    assert (repo / TARGET).is_file(), f"seal.sh phải ghi {TARGET}"
    leaked = leaked_files(repo, state["password"])
    assert not leaked, f"Giá trị rõ (hay base64 của nó) nằm trong repo: {leaked} (không in giá trị)"
    doc = yaml.safe_load((repo / TARGET).read_text(encoding="utf-8"))
    assert doc.get("kind") == "Secret" and doc.get("metadata", {}).get("name") == "olist-db", \
        "apiVersion, kind, metadata.name còn đọc được (chỉ mã hoá trường dữ liệu)"
    values = doc.get("stringData") or doc.get("data") or {}
    assert values and all(ENCRYPTED.match(str(v)) for v in values.values()), "Mọi giá trị trong stringData/data phải là ENC[...]"
    got = sorted(entry["recipient"] for entry in doc.get("sops", {}).get("age", []))
    assert got == sorted([state["team"][1], state["argocd"][1]]), "Tệp phải mã hoá cho đúng hai recipient của .sops.yaml"


def test_both_recipients_can_decrypt(tmp_path):
    state = sealed(tmp_path)
    assert state["result"].returncode == 0, "seal.sh lỗi, xem test_seal_encrypts_fields_for_both_recipients"
    for who in ("team", "argocd"):
        code, doc = decrypt(tmp_path, state["repo"], state[who][0])
        assert code == 0, f"Khoá của {who} không giải mã được {TARGET}"
        assert (doc.get("stringData") or {}).get("POSTGRES_PASSWORD") == state["password"], \
            f"Giải mã bằng khoá của {who} ra giá trị khác giá trị gốc (không in giá trị)"


def test_kustomize_includes_secret_and_workloads_use_it(tmp_path):
    ex.require_tool("kubectl", KUBECTL_MIN_VERSION)
    shop = ex.path("gitops/shop")
    kustomization = yaml.safe_load((shop / "kustomization.yaml").read_text(encoding="utf-8"))
    assert "olist-db.enc.yaml" in (kustomization.get("resources") or []), "kustomization.yaml phải liệt kê olist-db.enc.yaml"
    assert not kustomization.get("secretGenerator"), "Không sinh Secret từ tệp rõ bằng secretGenerator"
    work = tmp_path / "shop"
    shutil.copytree(shop, work)
    (work / "olist-db.enc.yaml").write_text(
        "apiVersion: v1\nkind: Secret\nmetadata:\n  name: olist-db\nstringData:\n  POSTGRES_PASSWORD: x\n", encoding="utf-8")
    result = run_sandboxed(["kubectl", "kustomize", str(work)], writable=[tmp_path], cwd=tmp_path, env={})
    assert result.returncode == 0, result.stderr[-800:]
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    text = {d["metadata"]["name"]: json.dumps(d) for d in docs if d["kind"] in ("Deployment", "StatefulSet")}
    for name in ("postgres", "api"):
        assert name in text, f"Cần workload {name}"
        assert '"name": "olist-db"' in text[name], f"{name} phải lấy biến từ Secret olist-db"
    assert not [d for d in docs if d["kind"] == "Secret" and d["metadata"]["name"] != "olist-db"], "Không thêm Secret rõ nào khác"


def test_application_uses_sops_plugin():
    app = application()
    source = app.get("spec", {}).get("source", {})
    assert source.get("repoURL") == "LAB_REPO_URL" and source.get("path") == "shop"
    assert (source.get("plugin") or {}).get("name") == KUBE_ARGOCD_CMP, \
        f"ArgoCD chỉ giải mã khi Application dùng plugin {KUBE_ARGOCD_CMP}"
    assert app["spec"].get("project") == "LAB_PROJECT" and app["spec"].get("destination", {}).get("namespace") == "LAB_NAMESPACE"
    assert (app["spec"].get("syncPolicy") or {}).get("automated") is not None, "Bật sync tự động"


@pytest.fixture(scope="module")
def deployed(tmp_path_factory):
    require_tools()
    ex.require_cluster()
    ex.require_argocd()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    tmp = tmp_path_factory.mktemp("sops")
    state: dict = {}
    with KubeLab() as lab:
        project = lab.argocd_project()
        team_key, team = age_keypair(tmp / "team", outside=[ex.target])
        password = secrets.token_urlsafe(18)
        plain = plain_secret(tmp / "plain", password)
        repo = stage(tmp, team, lab.sops_age_recipient)
        state.update(password=password, repo=repo, sealed=seal(tmp, repo, plain, team_key))
        if state["sealed"].returncode != 0 or leaked_files(repo, password) or not (repo / TARGET).is_file():
            yield lab, state
            return
        lab.gitops_repo(repo)
        text = json.dumps(application())
        for placeholder, value in (("LAB_REPO_URL", lab.repo_url), ("LAB_NAMESPACE", lab.namespace), ("LAB_PROJECT", project)):
            text = text.replace(placeholder, value)
        manifest = tmp / "application.json"
        manifest.write_text(text, encoding="utf-8")
        try:
            lab.apply_learner(manifest)
            state["status"] = lab.argocd_wait(APP, timeout=240)
        except pytest.fail.Exception as error:
            state["status"] = str(error)
        yield lab, state


def test_argocd_decrypts_and_app_is_ready(deployed):
    lab, state = deployed
    assert state["sealed"].returncode == 0, f"seal.sh lỗi: {state['sealed'].stderr.strip()[-500:]}"
    assert not leaked_files(state["repo"], state["password"]), "Repo có giá trị rõ, test không đẩy lên git server"
    status = state.get("status")
    assert isinstance(status, dict), f"Application chưa Synced, Healthy: {status}"
    result = lab.kubectl("exec", "deployment/api", "-c", "api", "--", "python", "-c", READYZ, check=False)
    assert result.stdout.startswith("200"), f"/readyz của api (db dùng mật khẩu đã giải mã): {result.stdout[-300:]}"


def test_pods_read_the_sealed_value(deployed):
    lab, state = deployed
    assert isinstance(state.get("status"), dict), "Application chưa sync được"
    secret = json.loads(lab.kubectl("get", "secret", "olist-db", "-o", "json").stdout)
    got = base64.b64decode(secret["data"]["POSTGRES_PASSWORD"]).decode()
    assert got == state["password"], "Secret olist-db trên cluster khác giá trị đã mã hoá (không in giá trị)"
    result = lab.kubectl("exec", "deployment/postgres", "--", "sh", "-c", PASSWORD_HASH, check=False)
    expected = hashlib.sha256(state["password"].encode()).hexdigest()
    assert result.stdout.split()[:1] == [expected], "POSTGRES_PASSWORD trong pod postgres khác giá trị đã mã hoá (chỉ so hash)"


def test_value_not_in_argocd_status(deployed):
    lab, state = deployed
    assert isinstance(state.get("status"), dict), "Application chưa sync được"
    app = lab.kubectl("get", "applications.argoproj.io", APP, "-o", "json").stdout
    described = lab.kubectl("describe", "applications.argoproj.io", APP).stdout
    encoded = [n.decode() for n in needles(state["password"])]
    assert not any(n in app or n in described for n in encoded), "Giá trị Secret xuất hiện trong Application (không in giá trị)"
