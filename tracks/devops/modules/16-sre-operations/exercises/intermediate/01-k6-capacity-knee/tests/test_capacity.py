import json
import re
from pathlib import Path

import pytest

import testkit
from testkit import DockerLab, Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
SERVER_IMAGE = "python:3.12.16-alpine3.24"
STEPS = [10, 20, 30, 40, 60, 80]
STEP_SECONDS = 5
CAPACITY_RPS = 50
PEAK = 300
ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|$")


@pytest.fixture(scope="module")
def capacity():
    return ex.module("capacity.py")


def sample() -> dict:
    return json.loads((FIXTURES / "summary-sample.json").read_text(encoding="utf-8"))


def row(rps, achieved, p95, error=0.0, avg=None):
    return {"rps": rps, "achieved_rps": achieved, "p95_ms": p95, "avg_ms": avg or p95, "error_rate": error}


def value(summary: dict, name: str, step: int, key: str) -> float:
    return summary["metrics"][f"{name}{{scenario:step_{step}}}"]["values"][key]


def test_step_metrics_from_summary(capacity):
    rows = capacity.step_metrics(sample(), STEPS, STEP_SECONDS)
    assert [r["rps"] for r in rows] == STEPS
    first, last = rows[0], rows[-1]
    assert first["achieved_rps"] == pytest.approx(10.0) and first["p95_ms"] == pytest.approx(41.31, abs=0.01)
    assert last["achieved_rps"] == pytest.approx(62.6) and last["avg_ms"] == pytest.approx(1237.07, abs=0.01)
    assert all(r["error_rate"] == 0 for r in rows)


def test_step_metrics_needs_submetrics(capacity):
    summary = sample()
    del summary["metrics"]["http_reqs{scenario:step_30}"]
    with pytest.raises(ValueError):
        capacity.step_metrics(summary, STEPS, STEP_SECONDS)


def test_knee_rules(capacity):
    assert capacity.knee(capacity.step_metrics(sample(), STEPS, STEP_SECONDS)) == 40
    rows = [row(10, 10, 50), row(20, 20, 60), row(30, 30, 70), row(40, 40, 90)]
    assert capacity.knee(rows) == 40
    assert capacity.knee(rows, slo_p95_ms=65) == 20
    assert capacity.knee([row(10, 10, 50), row(20, 20, 60, error=0.02), row(30, 30, 50)]) == 10, "Lỗi quá 1% là gãy"
    assert capacity.knee([row(10, 10, 50), row(20, 17, 60), row(30, 30, 50)]) == 10, "Không đạt 90% tải mục tiêu là gãy"
    assert capacity.knee([row(20, 20, 60), row(10, 10, 300), row(30, 30, 50)]) is None, "Phải xét bước theo thứ tự tăng dần"


def test_littles_law_and_replicas(capacity):
    assert capacity.littles_law(40, 41.0) == pytest.approx(1.64)
    assert capacity.littles_law(200, 250) == pytest.approx(50)
    assert capacity.replicas(300, 40) == 11
    assert capacity.replicas(300, 40, headroom=0, spare=0) == 8
    assert capacity.replicas(80, 40, headroom=0) == 3
    with pytest.raises(ValueError):
        capacity.replicas(300, 0)


def parse_report(text: str) -> tuple[dict[int, tuple[float, ...]], dict[str, str]]:
    rows = {int(m.group(1)): tuple(float(m.group(i)) for i in range(2, 6)) for line in text.splitlines()
            if (m := ROW.match(line.strip()))}
    facts = dict(re.findall(r"^(Điểm gãy|Đồng thời ở điểm gãy \(Little\)|Replica cho đỉnh \d+ rps): (.+)$", text, re.M))
    return rows, facts


def check_report(capacity, summary: dict, knee: int) -> None:
    text = capacity.report(summary, STEPS, STEP_SECONDS, PEAK)
    rows, facts = parse_report(text)
    assert sorted(rows) == STEPS, f"Bảng phải có đúng một dòng cho mỗi bước {STEPS}"
    for step, (achieved, p95, avg, error) in rows.items():
        assert achieved == pytest.approx(value(summary, "http_reqs", step, "count") / STEP_SECONDS, abs=0.051), step
        assert p95 == pytest.approx(value(summary, "http_req_duration", step, "p(95)"), abs=0.051), step
        assert avg == pytest.approx(value(summary, "http_req_duration", step, "avg"), abs=0.051), step
        assert error == pytest.approx(value(summary, "http_req_failed", step, "rate") * 100, abs=0.0051), step
    assert facts.get("Điểm gãy") == f"{knee} rps"
    expected = knee * value(summary, "http_req_duration", knee, "avg") / 1000
    assert float(facts["Đồng thời ở điểm gãy (Little)"]) == pytest.approx(expected, abs=0.006)
    assert int(facts[f"Replica cho đỉnh {PEAK} rps"]) == capacity.replicas(PEAK, knee)


def test_report_matches_sample(capacity):
    check_report(capacity, sample(), 40)


def test_load_test_finds_knee(capacity):
    ex.require_image(SERVER_IMAGE)
    ex.require_image(testkit.K6_IMAGE, f"Tải image k6 bằng: {testkit.K6_PULL}")
    with DockerLab() as lab:
        lab.start("api", SERVER_IMAGE, "python", "-u", "/srv/server.py", mounts=[(FIXTURES, "/srv")])
        lab.wait_log("api", "listening")
        result, summary = testkit.k6_run(lab, ex.path("load.js"), timeout=240,
                                         env={"TARGET": "http://api:8000", "STEPS": ",".join(map(str, STEPS)),
                                              "STEP_SECONDS": str(STEP_SECONDS)})
    assert summary is not None, f"k6 không chạy tới cuối:\n{result.stderr[-3000:]}"
    assert result.returncode == 0, f"k6 thoát mã {result.returncode}; threshold trong bài chỉ để ghi submetric:\n{result.stderr[-2000:]}"
    missing = [f"{n}{{scenario:step_{s}}}" for s in STEPS for n in ("http_req_duration", "http_req_failed", "http_reqs")
               if f"{n}{{scenario:step_{s}}}" not in summary["metrics"]]
    assert not missing, f"Tóm tắt k6 thiếu submetric: {', '.join(missing)}"
    for step in STEPS[:3]:
        count = value(summary, "http_reqs", step, "count")
        assert 0.9 * step * STEP_SECONDS <= count <= 1.1 * step * STEP_SECONDS + 1, \
            f"Bước {step} rps gửi {count} request trong {STEP_SECONDS} giây: tải phải đến đều theo tốc độ, không phụ thuộc server"
    rows = capacity.step_metrics(summary, STEPS, STEP_SECONDS)
    knee = capacity.knee(rows)
    assert knee is not None and 20 <= knee <= CAPACITY_RPS, f"Điểm gãy {knee} rps không hợp lý với service này"
    assert value(summary, "http_req_duration", STEPS[-1], "p(95)") > 200, "Bước cao nhất phải vượt công suất của service"
    check_report(capacity, summary, knee)
