from pathlib import Path

import pytest

import testkit
from testkit import DockerLab, Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
SERVER_IMAGE = "python:3.12.16-alpine3.24"
FORECAST_RPS = 80
SECONDS = 6


def run(script: Path, release: str) -> tuple:
    ex.require_image(SERVER_IMAGE)
    ex.require_image(testkit.K6_IMAGE, f"Tải image k6 bằng: {testkit.K6_PULL}")
    with DockerLab() as lab:
        lab.start("api", SERVER_IMAGE, "python", "-u", "/srv/orders.py", mounts=[(FIXTURES, "/srv")], env={"RELEASE": release})
        lab.wait_log("api", "listening")
        result, summary = testkit.k6_run(lab, script, env={"TARGET": "http://api:8000"}, timeout=180)
    assert summary is not None, f"k6 không chạy tới cuối (mã {result.returncode}):\n{result.stderr[-3000:]}"
    return result, summary


def requests(summary: dict) -> int:
    return int(summary["metrics"]["http_reqs"]["values"]["count"])


def test_release_2_3_0_passes_at_forecast_traffic():
    result, summary = run(ex.path("load.js"), "2.3.0")
    assert result.returncode == 0, f"Bản 2.3.0 chạy tốt ngoài production mà kịch bản báo hỏng (mã {result.returncode})"
    sent = requests(summary)
    expected = FORECAST_RPS * SECONDS
    assert 0.9 * expected <= sent <= 1.1 * expected + 1, \
        f"Kịch bản gửi {sent} request trong {SECONDS} giây; dự báo ngày ra mắt là {FORECAST_RPS} request/giây"


def test_release_2_4_0_is_rejected():
    result, _ = run(ex.path("load.js"), "2.4.0")
    assert result.returncode == 99, "Bản 2.4.0 làm khách không đặt được hàng ngày ra mắt mà kịch bản vẫn cho qua"


def test_release_2_4_1_is_rejected():
    result, _ = run(ex.path("load.js"), "2.4.1")
    assert result.returncode == 99, "Bản 2.4.1 vi phạm SLO ở traffic dự báo mà kịch bản vẫn cho qua"


def test_original_script_reproduces_launch_day():
    result, summary = run(FIXTURES / "incident" / "load.js", "2.4.0")
    assert result.returncode == 0 and requests(summary) > 0, "Kịch bản gốc phải tái hiện được tình huống ngày ra mắt"
