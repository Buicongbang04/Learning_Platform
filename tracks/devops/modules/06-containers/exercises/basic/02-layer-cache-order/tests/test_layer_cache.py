import json
import re
import shutil
import uuid
from pathlib import Path

import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
BASE = "python:3.12.16-slim-trixie"
FIXTURES = Path(__file__).parent / "fixtures"
APP = FIXTURES / "app"
SECRET = "OLIST_EXPORT_TOKEN=dev-only-4f9c2a7e-khong-duoc-vao-image\n"
LEAKS = (".env", "export_checks.py", "notes.md")
NETWORK_ERRORS = (
    "Temporary failure in name resolution", "Temporary failure resolving", "Could not resolve", "Failed to establish a new "
    "connection", "Network is unreachable", "NewConnectionError", "Connection timed out", "Read timed out",
)
FIND_LEAKS = (
    "import json, os; "
    f"names = {LEAKS!r}; "
    "skip = ('/proc', '/sys', '/dev'); "
    "print(json.dumps(sorted(os.path.join(d, f) for d, _, fs in os.walk('/') if not d.startswith(skip) "
    "for f in fs if f in names)))"
)


def make_context(dest: Path, dockerfile: Path, dockerignore: Path | None, build_id: str) -> Path:
    shutil.copytree(APP, dest, ignore=shutil.ignore_patterns("__pycache__"))
    (dest / ".env").write_text(SECRET, encoding="utf-8")
    shutil.copyfile(dockerfile, dest / "Dockerfile")
    if dockerignore is not None:
        shutil.copyfile(dockerignore, dest / ".dockerignore")
    code = dest / "export_orders.py"
    code.write_text(re.sub(r'^BUILD_ID = ".*"$', f'BUILD_ID = "{build_id}"', code.read_text(encoding="utf-8"), flags=re.M),
                    encoding="utf-8")
    return dest


def build(lab: DockerLab, context: Path, alias: str) -> str:
    try:
        return lab.build(context, alias)
    except pytest.fail.Exception as error:
        if any(text in str(error) for text in NETWORK_ERRORS):
            pytest.skip("Build cần mạng ở lần đầu để tải gói pip (BuildKit giữ cache cho lần sau). Kiểm kết nối mạng rồi "
                        "chạy lại.")
        raise


def deps_step(history: list[dict], base: list[dict]) -> dict | None:
    inherited = {(h.get("CreatedBy"), h.get("CreatedAt")) for h in base}
    steps = [h for h in history if (h.get("CreatedBy"), h.get("CreatedAt")) not in inherited
             and h.get("CreatedBy", "").startswith("RUN") and "pip" in h["CreatedBy"] and "install" in h["CreatedBy"]]
    return steps[0] if steps else None


def two_builds(lab: DockerLab, workdir: Path, dockerfile: Path, dockerignore: Path | None, prefix: str) -> dict:
    first, second = uuid.uuid4().hex[:12], uuid.uuid4().hex[:12]
    tag1 = build(lab, make_context(workdir / f"{prefix}-1", dockerfile, dockerignore, first), f"{prefix}-1")
    history1 = lab.history(tag1)
    tag2 = build(lab, make_context(workdir / f"{prefix}-2", dockerfile, dockerignore, second), f"{prefix}-2")
    return {"history1": history1, "history2": lab.history(tag2), "tag2": tag2, "build_id": second, "prefix": prefix}


def cache_problems(lab: DockerLab, builds: dict) -> list[str]:
    found = []
    base = lab.history(BASE)
    step1, step2 = deps_step(builds["history1"], base), deps_step(builds["history2"], base)
    if step1 is None or step2 is None:
        return [f"Không thấy bước RUN ... pip install của bạn trong lịch sử image cuối (bài này dùng một stage từ {BASE})"]
    if step1["CreatedAt"] != step2["CreatedAt"]:
        found.append(f"Chỉ sửa export_orders.py mà bước `{step2['CreatedBy'][:80]}` vẫn chạy lại (CreatedAt "
                     f"{step1['CreatedAt']} rồi {step2['CreatedAt']}): layer dependency không lấy từ cache")
    result = lab.run_once(f"{builds['prefix']}-run", builds["tag2"], timeout=60)
    try:
        output = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        output = {}
    if result.returncode != 0 or output.get("build_id") != builds["build_id"]:
        found.append(f"Image build lại phải chạy được và in build_id mới {builds['build_id']}, nhận mã "
                     f"{result.returncode}: {(result.stdout + result.stderr)[-300:]}")
    return found


def leak_problems(lab: DockerLab, builds: dict) -> list[str]:
    result = lab.run_once(f"{builds['prefix']}-leaks", builds["tag2"], "-c", FIND_LEAKS, entrypoint="python3", timeout=60)
    assert result.returncode == 0, f"Không chạy được python3 trong image: {result.stderr[-300:]}"
    leaked = json.loads(result.stdout.strip().splitlines()[-1])
    return [f"Tệp không được vào image: {path}" for path in leaked]


def settle(build_all) -> dict:
    try:
        return build_all()
    except pytest.fail.Exception as error:
        return {"error": str(error)}


def unwrap(builds: dict) -> dict:
    if "error" in builds:
        pytest.fail(builds["error"], pytrace=False)
    return builds


@pytest.fixture(scope="module")
def lab():
    ex.require_image(BASE)
    with DockerLab() as lab:
        yield lab


@pytest.fixture(scope="module")
def learner(lab, tmp_path_factory):
    workdir = tmp_path_factory.mktemp("ctx")
    return settle(lambda: two_builds(lab, workdir, ex.path("Dockerfile"), ex.path(".dockerignore"), "export"))


@pytest.fixture(scope="module")
def starter(lab, tmp_path_factory):
    starter = FIXTURES / "starter"
    return two_builds(lab, tmp_path_factory.mktemp("starter"), starter / "Dockerfile", starter / ".dockerignore", "starter")


def test_dependency_layer_reused_after_code_change(lab, learner):
    found = cache_problems(lab, unwrap(learner))
    assert not found, "\n".join(found)


def test_secrets_and_dev_files_stay_out_of_image(lab, learner):
    found = leak_problems(lab, unwrap(learner))
    assert not found, "\n".join(found)


def test_checks_catch_starter(lab, starter):
    cache = "\n".join(cache_problems(lab, starter))
    assert "không lấy từ cache" in cache, cache
    assert "build_id mới" not in cache, cache
    leaks = "\n".join(leak_problems(lab, starter))
    assert ".env" in leaks and "export_checks.py" in leaks, leaks
