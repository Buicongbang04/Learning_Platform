import re
from pathlib import Path

import pytest
import yaml

from testkit import KUBECTL_MIN_VERSION, Exercise, run_sandboxed

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
ENVS = {"staging": "olist-staging", "production": "olist-production"}
IMAGE = "devops-track/olist-shop"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
KEYWORDS = {
    1: (("môi trường", "environment"), ("staging",), ("production",)),
    2: (("base",), ("overlay", "envs/"), ("app-of-apps", "app of apps", "applicationset")),
    3: (("pull request", "pr"), ("staging",), ("digest", "sha256"), ("tự động", "automated", "bot", "ci")),
    4: (("appproject",), ("codeowners", "branch protection", "review")),
    5: (("sops", "external secrets", "vault"), ("recipient", "khoá", "key")),
    6: (("revert",), ("drift", "self-heal", "selfheal")),
    7: (("branch",), ("helm",), ("applicationset", "kargo", "flux")),
}
MIN_BULLETS = {3: 4, 4: 3, 6: 3, 7: 4}


def render(path: Path, tmp_path: Path) -> list[dict]:
    ex.require_tool("kubectl", KUBECTL_MIN_VERSION)
    tmp_path.mkdir(parents=True, exist_ok=True)
    result = run_sandboxed(["kubectl", "kustomize", str(path)], writable=[tmp_path], cwd=tmp_path, env={}, readonly=[path])
    assert result.returncode == 0, f"kubectl kustomize {path} lỗi:\n{result.stderr[-1500:]}"
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def kustomization(env: str) -> dict:
    return yaml.safe_load((ex.path(f"repo/envs/{env}") / "kustomization.yaml").read_text(encoding="utf-8")) or {}


def applications() -> dict[str, dict]:
    found = {}
    for path in sorted(ex.path("repo/apps").glob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if doc and doc.get("kind") == "Application":
                found[doc["metadata"]["name"]] = doc
    return found


def deployment(docs, name: str) -> dict:
    found = [d for d in docs if d["kind"] == "Deployment" and d["metadata"]["name"] == name]
    assert found, f"Không thấy Deployment {name}"
    return found[0]


@pytest.mark.parametrize("env", ENVS)
def test_overlay_builds_on_shared_base(env, tmp_path):
    resources = kustomization(env).get("resources") or []
    assert any(Path(r).as_posix().rstrip("/").endswith("base") for r in resources), f"envs/{env} phải dùng chung base"
    docs = render(ex.path(f"repo/envs/{env}"), tmp_path)
    assert {d["metadata"].get("namespace") for d in docs} == {ENVS[env]}, f"Mọi object của {env} nằm trong {ENVS[env]}"
    assert deployment(docs, "api")


def test_images_pinned_and_production_by_digest(tmp_path):
    images = {}
    for env in ENVS:
        entries = [i for i in kustomization(env).get("images") or [] if i.get("name") == IMAGE]
        assert entries, f"envs/{env} khai báo images: cho {IMAGE} (promote là sửa đúng một dòng)"
        images[env] = entries[0]
        container = deployment(render(ex.path(f"repo/envs/{env}"), tmp_path / env), "api")["spec"]["template"]["spec"]["containers"][0]
        assert not container["image"].endswith(":latest") and container["image"] != IMAGE, f"{env}: image không được trôi"
    assert DIGEST.match(str(images["production"].get("digest", ""))), "production ghim image theo digest (sha256:...)"


def test_production_hardened(tmp_path):
    staging = render(ex.path("repo/envs/staging"), tmp_path / "s")
    production = render(ex.path("repo/envs/production"), tmp_path / "p")
    assert deployment(production, "api")["spec"].get("replicas", 1) >= 2, "production chạy ít nhất 2 replica api"
    assert deployment(staging, "api")["spec"].get("replicas", 1) == 1, "staging 1 replica cho rẻ"
    assert any(d["kind"] == "PodDisruptionBudget" for d in production), "production có PodDisruptionBudget cho api"
    assert not any(d["kind"] == "PodDisruptionBudget" for d in staging), "PDB là của production (overlay), không đặt ở base"


def test_applications_one_per_env_same_revision():
    apps = applications()
    by_path = {a["spec"]["source"].get("path"): a for a in apps.values()}
    for env, namespace in ENVS.items():
        app = by_path.get(f"envs/{env}")
        assert app, f"Cần một Application trỏ envs/{env}"
        assert app["spec"]["destination"]["namespace"] == namespace
        assert app["spec"].get("project") not in (None, "default"), f"Application {env} dùng AppProject riêng, không dùng default"
    projects = {by_path[f"envs/{env}"]["spec"]["project"] for env in ENVS}
    assert len(projects) == 2, "staging và production dùng hai AppProject khác nhau"
    revisions = {a["spec"]["source"].get("targetRevision") for a in apps.values()}
    assert revisions <= {"main", "HEAD"}, f"Mọi môi trường theo cùng nhánh main (môi trường là thư mục, không là nhánh): {revisions}"
    staging = by_path["envs/staging"]["spec"].get("syncPolicy") or {}
    assert staging.get("automated"), "staging sync tự động"


def test_root_app_of_apps():
    roots = [a for a in applications().values() if a["spec"]["source"].get("path") == "apps"]
    assert len(roots) == 1, "Cần đúng một Application gốc (app-of-apps) trỏ thư mục apps"
    assert roots[0]["spec"]["destination"]["namespace"] == "argocd", "Application con nằm trong namespace argocd"


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def design_problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if "```" not in section(doc, 2):
        found.append("Phần 2: cần cây thư mục trong khối code")
    if "```mermaid" not in section(doc, 3):
        found.append("Phần 3: cần sơ đồ mermaid cho đường promote")
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = " ".join(section(doc, number).split()).lower()
        for group in groups:
            if not any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


def test_design_doc():
    found = design_problems(ex.read("DESIGN.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = design_problems((FIXTURES / "DESIGN.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and "Phần 3: cần sơ đồ mermaid cho đường promote" in found


def test_checks_catch_weak_design():
    found = "\n".join(design_problems((FIXTURES / "DESIGN.weak.md").read_text(encoding="utf-8")))
    for needle in ("Phần 3: chưa nói tới digest", "Phần 4: chưa nói tới appproject", "Phần 6: chưa nói tới revert",
                   "Phần 7: ít nhất 4", "Phần 3: cần sơ đồ mermaid"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_design_passes():
    found = design_problems((FIXTURES / "DESIGN.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)
