import json
import shutil
import sys
from pathlib import Path

import mlopskit
import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))


class Broken:
    def __init__(self, message: str) -> None:
        self.message = message


def need(value):
    if isinstance(value, Broken):
        pytest.fail(value.message, pytrace=False)
    return value


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    from make_model import build

    context = tmp_path_factory.mktemp("ctx") / "context"
    shutil.copytree(FIXTURES / "service", context)
    build(context / "model.joblib")
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


def serve(lab, image, alias, env=None):
    image = need(image)
    lab.start(alias, image, ports=[8000], env=env or {})
    url = f"http://127.0.0.1:{lab.port(alias, 8000)}"
    lab.wait_http(alias, url + "/healthz")
    return url


def run_k6(url, p95_ms=300):
    result = mlopskit.k6_run(ex.path("loadtest.js"), {"TARGET": url, "P95_MS": str(p95_ms)})
    summary = json.loads(result.stdout) if result.stdout.strip() else {}
    return result, summary.get("metrics", {})


@pytest.fixture(scope="module")
def healthy(image, lab):
    url = serve(lab, image, "healthy")
    return run_k6(url)


@pytest.fixture(scope="module")
def slow(image, lab):
    url = serve(lab, image, "slow", {"SLOW_MS": "450"})
    return run_k6(url)


def test_healthy_service_passes_the_gate(healthy):
    result, _ = healthy
    assert result.returncode == 0, f"k6 thoát mã {result.returncode}, ngưỡng không đạt hoặc script lỗi:\n{result.stderr[-1500:]}"


def test_slow_service_fails_the_gate(slow):
    result, _ = slow
    assert result.returncode == 99, (
        f"Service chậm (~450 ms) phải làm k6 thoát mã 99 (ngưỡng p95 vi phạm), nhận {result.returncode}:\n{result.stderr[-1500:]}"
    )


def test_thresholds_apply_to_measure_phase_only(healthy):
    _, metrics = healthy
    for name in ("http_req_duration{scenario:measure}", "http_req_failed{scenario:measure}"):
        assert name in metrics, f"Thiếu ngưỡng trên `{name}`: ngưỡng phải áp lên giai đoạn measure, không áp lên warmup"
    assert "p(95)" in metrics["http_req_duration{scenario:measure}"]


def test_p95_limit_comes_from_env(healthy, slow):
    for _, metrics in (healthy, slow):
        thresholds = metrics["http_req_duration{scenario:measure}"].get("thresholds", {})
        assert any("p(95)<300" in key.replace(" ", "") for key in thresholds), f"Ngưỡng p95 phải đọc từ P95_MS: {thresholds}"


def test_load_shape_is_warmup_then_measure(healthy):
    _, metrics = healthy
    total = metrics["http_reqs"]["count"]
    assert 255 <= total <= 285, (
        f"Cần scenario warmup (10 req/s trong 3 s, ~30 request) rồi measure (30 req/s trong 8 s, ~240 request), tổng ~270; đo được {total}"
    )


def test_checks_validate_the_response_body(healthy):
    result, metrics = healthy
    checks = metrics.get("checks", {})
    assert checks.get("passes", 0) >= 3 * 200, "Mỗi request cần 3 check: status 200, có model_version, đủ số dự đoán"
    assert checks.get("fails", 0) == 0
