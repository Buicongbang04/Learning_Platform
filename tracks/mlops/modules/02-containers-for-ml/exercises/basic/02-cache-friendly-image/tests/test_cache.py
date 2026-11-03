import shutil
import sys
from pathlib import Path

import mlopskit
import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))
MAX_MB = 600
JUNK_MB = 150


class Broken:
    def __init__(self, message: str) -> None:
        self.message = message


def need(value):
    if isinstance(value, Broken):
        pytest.fail(value.message, pytrace=False)
    return value


def instructions(text: str) -> list[tuple[str, str]]:
    found = []
    for line in text.replace("\\\n", " ").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            keyword, _, rest = line.partition(" ")
            found.append((keyword.upper(), rest.strip()))
    return found


def make_context(target: Path) -> Path:
    from make_model import build

    context = target / "context"
    shutil.copytree(FIXTURES / "service", context)
    build(context / "model.joblib")
    (context / "notebooks").mkdir()
    with open(context / "notebooks" / "trips-2019-01.csv", "wb") as junk:
        junk.write(b"\0" * JUNK_MB * 1_000_000)
    (context / "app" / "__pycache__").mkdir()
    (context / "app" / "__pycache__" / "serve.cpython-312.pyc").write_bytes(b"x" * 1000)
    shutil.copyfile(ex.path("Dockerfile"), context / "Dockerfile")
    shutil.copyfile(ex.path(".dockerignore"), context / ".dockerignore")
    return context


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    return ex.read("Dockerfile")


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    context = make_context(tmp_path_factory.mktemp("ctx"))
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


def test_dependency_layer_precedes_source_copy(dockerfile_text):
    steps = instructions(dockerfile_text)
    stage_steps = []
    for keyword, rest in steps:
        if keyword == "FROM":
            stage_steps = []
        stage_steps.append((keyword, rest))
        if keyword == "RUN" and "pip install" in rest:
            copies = [text for key, text in stage_steps if key == "COPY" and "--from" not in text]
            assert copies, "Phải COPY requirements.txt trước khi pip install"
            for text in copies:
                assert text.split()[0] != "." and "app" not in text.split()[:-1], (
                    f"`COPY {text}` đứng trước pip install: sửa một dòng code là cài lại toàn bộ dependency"
                )
            assert any("requirements.txt" in text for text in copies), "pip install chưa dựa trên requirements.txt đã COPY riêng"
            return
    pytest.fail("Không thấy bước RUN pip install")


def test_multi_stage_final_image_has_no_build_cache(dockerfile_text):
    froms = [rest for keyword, rest in instructions(dockerfile_text) if keyword == "FROM"]
    assert len(froms) >= 2, "Dùng multi-stage: một stage cài dependency, một stage cuối chỉ chép kết quả"
    assert any("COPY" == keyword and "--from" in rest for keyword, rest in instructions(dockerfile_text)), (
        "Stage cuối phải COPY --from=<stage cài dependency>"
    )
    pins = [text.split()[0] for text in froms]
    assert all(":" in pin and not pin.endswith(":latest") and pin.split(":")[1] != "3.12" for pin in pins), (
        f"Ghim tag đầy đủ (vd. 3.12.11-slim), không dùng tag trôi: {pins}"
    )
    assert all("slim" in pin for pin in pins), "Base phải là biến thể slim"


def test_pip_cache_not_kept(dockerfile_text):
    installs = [rest for keyword, rest in instructions(dockerfile_text) if keyword == "RUN" and "pip install" in rest]
    assert installs and all("--no-cache-dir" in rest for rest in installs)


def test_image_stays_small_despite_big_context(image):
    image = need(image)
    megabytes = mlopskit.image_size_bytes(image) / 1_000_000
    assert megabytes < MAX_MB, f"Image nặng {megabytes:.0f} MB (ngưỡng {MAX_MB} MB): dữ liệu hoặc cache nào đó lọt vào image"


def test_dockerignore_keeps_data_out_of_the_image(image, lab):
    image = need(image)
    listing = lab.run_once("ls", image, "-R", "/srv", entrypoint="ls")
    assert listing.returncode == 0, listing.stderr
    assert "notebooks" not in listing.stdout and "trips-2019-01.csv" not in listing.stdout, (
        "Thư mục notebooks/ nằm trong image: thêm vào .dockerignore"
    )
    assert "__pycache__" not in listing.stdout, "__pycache__ nằm trong image: thêm vào .dockerignore"


def test_service_still_serves(image, lab):
    image = need(image)
    lab.start("api", image, ports=[8000])
    lab.wait_http("api", f"http://127.0.0.1:{lab.port('api', 8000)}/healthz")
