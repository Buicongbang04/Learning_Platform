import re

import joblib
import shutil
import sys
from pathlib import Path

import httpx
import mlopskit
import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))
MAX_MB = 600


def instructions(text: str) -> list[tuple[str, str]]:
    found = []
    for line in text.replace("\\\n", " ").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            keyword, _, rest = line.partition(" ")
            found.append((keyword.upper(), rest.strip()))
    return found


class Broken:
    def __init__(self, message: str) -> None:
        self.message = message


def need(value):
    if isinstance(value, Broken):
        pytest.fail(value.message, pytrace=False)
    return value


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    return ex.read("Dockerfile")


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    from make_model import build

    context = tmp_path_factory.mktemp("ctx") / "context"
    shutil.copytree(FIXTURES / "service", context)
    build(context / "model.joblib")
    shutil.copyfile(ex.path("Dockerfile"), context / "Dockerfile")
    manager = mlopskit.built_image(context)
    try:
        tag = manager.__enter__()
    except pytest.fail.Exception as error:
        yield Broken(str(error))
        return
    try:
        yield tag
    finally:
        manager.__exit__(None, None, None)


@pytest.fixture(scope="module")
def lab():
    with DockerLab() as lab:
        yield lab


@pytest.fixture(scope="module")
def api(image, lab):
    if isinstance(image, Broken):
        return image
    try:
        lab.start("api", image, ports=[8000])
        url = f"http://127.0.0.1:{lab.port('api', 8000)}"
        lab.wait_http("api", url + "/healthz")
    except pytest.fail.Exception as error:
        return Broken(str(error))
    return url


def test_base_image_is_pinned_slim(dockerfile_text):
    bases = [rest.split()[0] for keyword, rest in instructions(dockerfile_text) if keyword == "FROM"]
    assert bases, "Dockerfile chưa có FROM"
    for base in bases:
        assert ":" in base and not base.endswith(":latest"), f"{base}: phải ghim tag phiên bản, không dùng latest"
        assert re.search(r":\d+\.\d+", base), f"{base}: tag phải có phiên bản cụ thể, vd. python:3.12.11-slim"
        assert "slim" in base or "alpine" in base, f"{base}: dùng biến thể slim cho image nhỏ"


def test_dependencies_installed_without_pip_cache(dockerfile_text):
    installs = [rest for keyword, rest in instructions(dockerfile_text) if keyword == "RUN" and "pip install" in rest]
    assert installs, "Chưa có bước cài dependency bằng pip install"
    assert all("--no-cache-dir" in rest or "PIP_NO_CACHE_DIR" in dockerfile_text for rest in installs), (
        "pip install phải kèm --no-cache-dir, nếu không cache wheel nằm lại trong layer"
    )


def test_has_user_instruction(dockerfile_text):
    users = [rest for keyword, rest in instructions(dockerfile_text) if keyword == "USER"]
    assert users, "Chưa có USER: container sẽ chạy bằng root"
    assert users[-1] not in {"root", "0"}, "USER cuối cùng không được là root"


def test_image_size_under_limit(image):
    image = need(image)
    megabytes = mlopskit.image_size_bytes(image) / 1_000_000
    assert megabytes < MAX_MB, f"Image nặng {megabytes:.0f} MB, ngưỡng {MAX_MB} MB"


def test_runs_as_non_root(image, lab):
    image = need(image)
    result = lab.run_once("whoami", image, "-u", entrypoint="id")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() != "0", "Container đang chạy bằng root (uid 0)"


def test_healthz_returns_200(api):
    api = need(api)
    response = httpx.get(api + "/healthz", timeout=5)
    assert response.status_code == 200
    assert response.json()["features"] == ["distance_km", "hour", "passengers"]


def test_predict_uses_model_inside_image(api, tmp_path):
    api = need(api)
    response = httpx.post(api + "/predict", json={"rows": [[5, 8, 1], [20, 3, 2]]}, timeout=5)
    assert response.status_code == 200
    from make_model import build

    expected = build(tmp_path / "model.joblib")

    local = joblib.load(expected)["model"].predict([[5, 8, 1], [20, 3, 2]])
    assert response.json()["predictions"] == pytest.approx(list(local), rel=1e-6)


def test_container_reports_docker_healthcheck(image):
    image = need(image)
    assert mlopskit.image_has_healthcheck(image), "Dockerfile chưa có HEALTHCHECK"
