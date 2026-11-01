import json
import re
import shutil
from pathlib import Path

import httpx
import pytest

from testkit import ROOT, DockerLab, Exercise

ex = Exercise(__file__)
BASE = "python:3.12.16-slim-trixie"
APP = ROOT / "tracks" / "devops" / "sample-app"
FIXTURES = Path(__file__).parent / "fixtures"
BUILD_TOOLS = ("gcc", "cc", "g++", "c++", "make", "ld")
ROOT_USERS = {"", "root", "0", "0:0", "root:root", "root:0", "0:root"}
SIZE_RATIO = 0.75
NETWORK_ERRORS = (
    "Temporary failure in name resolution", "Temporary failure resolving", "Could not resolve", "Failed to establish a new "
    "connection", "Network is unreachable", "NewConnectionError", "Connection timed out", "Read timed out",
)
PROBE = (
    "import json, os, shutil; "
    f"print(json.dumps({{'uid': os.getuid(), 'tools': [t for t in {BUILD_TOOLS!r} if shutil.which(t)]}}))"
)


class Images:
    def __init__(self, lab: DockerLab, workdir: Path) -> None:
        self.lab = lab
        self.workdir = workdir
        self.results: dict[str, tuple[str, object]] = {}

    def context(self, dockerfile: Path, name: str) -> Path:
        dest = self.workdir / name
        shutil.copytree(APP / "olist_shop", dest / "olist_shop", ignore=shutil.ignore_patterns("__pycache__", "*.db"))
        shutil.copyfile(APP / "requirements.txt", dest / "requirements.txt")
        shutil.copyfile(dockerfile, dest / "Dockerfile")
        return dest

    def build(self, dockerfile: Path, alias: str) -> str:
        try:
            return self.lab.build(self.context(dockerfile, alias), alias)
        except pytest.fail.Exception as error:
            if any(text in str(error) for text in NETWORK_ERRORS):
                pytest.skip("Build cần mạng ở lần đầu để tải gói apt và pip (BuildKit giữ cache cho lần sau). Kiểm kết nối "
                            "mạng rồi chạy lại.")
            raise

    def get(self, alias: str, dockerfile: Path) -> str:
        if alias not in self.results:
            try:
                self.results[alias] = ("ok", self.build(dockerfile, alias))
            except pytest.skip.Exception as error:
                self.results[alias] = ("skip", str(error))
            except pytest.fail.Exception as error:
                self.results[alias] = ("fail", str(error))
        status, value = self.results[alias]
        if status == "skip":
            pytest.skip(value)
        if status == "fail":
            pytest.fail(value, pytrace=False)
        return value


@pytest.fixture(scope="module")
def lab():
    ex.require_image(BASE)
    with DockerLab() as lab:
        yield lab


@pytest.fixture(scope="module")
def images(lab, tmp_path_factory):
    return Images(lab, tmp_path_factory.mktemp("ctx"))


@pytest.fixture(scope="module")
def starter_tag(images):
    return images.get("starter", FIXTURES / "Dockerfile.starter")


@pytest.fixture(scope="module")
def learner_tag(images):
    return images.get("api", ex.path("Dockerfile"))


def probe(lab: DockerLab, alias: str, tag: str) -> dict:
    result = lab.run_once(alias, tag, "-c", PROBE, entrypoint="python3")
    assert result.returncode == 0, f"Không chạy được python3 trong image: {result.stderr[-500:]}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def shell_form(command: list[str] | None) -> bool:
    return bool(command) and command[:2] in (["/bin/sh", "-c"], ["sh", "-c"])


def image_problems(lab: DockerLab, tag: str, dockerfile: str, starter_size: int | None, alias: str) -> list[str]:
    found = []
    if len(re.findall(r"^\s*FROM\s", dockerfile, re.M | re.I)) < 2:
        found.append("Dockerfile chỉ có 1 stage: cần stage build và stage runtime riêng (multi-stage)")
    info = lab.image_inspect(tag)
    config = info["Config"]
    facts = probe(lab, f"{alias}-probe", tag)
    if (config.get("User") or "") in ROOT_USERS:
        found.append("Image không khai báo USER khác root")
    if facts["uid"] == 0:
        found.append("Tiến trình trong container chạy với UID 0 (root)")
    if facts["tools"]:
        found.append(f"Stage cuối còn công cụ build: {', '.join(facts['tools'])}")
    if shell_form(config.get("Entrypoint")) or (not config.get("Entrypoint") and shell_form(config.get("Cmd"))):
        found.append(f"CMD/ENTRYPOINT dạng shell ({config.get('Entrypoint') or config.get('Cmd')}): /bin/sh là PID 1")
    if not (config.get("Healthcheck") or {}).get("Test") or config["Healthcheck"]["Test"] == ["NONE"]:
        found.append("Image không có HEALTHCHECK")
    if starter_size and info["Size"] > SIZE_RATIO * starter_size:
        found.append(f"Image {info['Size'] / 1e6:.0f} MB, phải nhỏ hơn {SIZE_RATIO:.0%} image của starter "
                     f"({starter_size / 1e6:.0f} MB), tức dưới {SIZE_RATIO * starter_size / 1e6:.0f} MB")
    return found


@pytest.fixture(scope="module")
def api(lab, learner_tag):
    lab.start("api", learner_tag, ports=[8000], env={"DATABASE_URL": "sqlite:////tmp/olist.db", "APP_VERSION": "m06-basic01"})
    url = f"http://127.0.0.1:{lab.port('api', 8000)}"
    lab.wait_http("api", url + "/healthz", timeout=90)
    return url


def test_image_meets_policy(lab, learner_tag, starter_tag):
    starter_size = lab.image_inspect(starter_tag)["Size"]
    found = image_problems(lab, learner_tag, ex.read("Dockerfile"), starter_size, "api")
    assert not found, "\n".join(found)


def test_healthz_answers(api):
    response = httpx.get(api + "/healthz", timeout=10)
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "version": "m06-basic01"}


def test_healthcheck_command_succeeds(lab, learner_tag, api):
    test = (lab.image_inspect(learner_tag)["Config"].get("Healthcheck") or {}).get("Test") or []
    if not test or test[0] == "NONE":
        pytest.fail("Image không có HEALTHCHECK")
    command = ["/bin/sh", "-c", test[1]] if test[0] == "CMD-SHELL" else test[1:]
    result = lab.exec("api", *command, timeout=30)
    assert result.returncode == 0, (f"Lệnh HEALTHCHECK {command} trả mã {result.returncode} trong container đang chạy:\n"
                                    f"{(result.stdout + result.stderr)[-800:]}")


def test_checks_catch_starter(lab, starter_tag):
    found = image_problems(lab, starter_tag, (FIXTURES / "Dockerfile.starter").read_text(encoding="utf-8"), None, "starter")
    joined = "\n".join(found)
    assert "1 stage" in joined
    assert "USER khác root" in joined and "UID 0" in joined
    assert "gcc" in joined and "make" in joined
    assert "dạng shell" in joined
    assert "HEALTHCHECK" in joined
