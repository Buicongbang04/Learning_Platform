import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import DockerLab, Exercise, ObsStack

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
APP = testkit.ROOT / "tracks" / "devops" / "sample-app"
PLACEHOLDERS = {"request_logs": "$request_id", "trace_id_of_request": "$request_id", "worker_logs_of_trace": "$trace_id",
                "errors_by_path": None}
TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
ERRORS = 4


def queries() -> dict:
    try:
        data = yaml.safe_load(ex.read("queries.yaml"))
    except yaml.YAMLError as error:
        pytest.fail(f"queries.yaml không phải YAML hợp lệ: {error}")
    assert isinstance(data, dict), "queries.yaml phải là một mapping"
    return data


def test_queries_filled():
    data = queries()
    for name, placeholder in PLACEHOLDERS.items():
        query = str(data.get(name) or "")
        assert query.strip() and "TODO" not in query, f"{name}: chưa viết query"
        if placeholder:
            assert placeholder in query, f"{name}: query phải dùng {placeholder} (test thay bằng giá trị thật)"
    assert re.search(r"\bcount_over_time\b|\brate\b", data["errors_by_path"]), "errors_by_path là metric query (count_over_time hay rate)"
    assert re.search(r"\bby\s*\(\s*path\s*\)", data["errors_by_path"]), "errors_by_path cần gộp theo path"


def olist_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(APP / "olist_shop", project / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(APP / "requirements.txt", project)
    shutil.copy(testkit.KUBE_OLIST_DOCKERFILE, project / "Dockerfile")
    shutil.copy(FIXTURES / "compose.yaml", project / "compose.yaml")
    return project


def lines_of(result: list) -> list[tuple[dict, str]]:
    return [(stream.get("stream") or {}, value) for stream in result for _, value in stream.get("values") or []]


def query_loki(stack: ObsStack, data: dict, name: str, **values: str) -> list:
    query = str(data[name])
    for key, value in values.items():
        query = query.replace(f"${key}", value)
    return stack.loki_query(query, since=900, limit=500, timeout=45)


def parse(line: str) -> dict:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {}


def server_trace(stack: ObsStack, request_id: str) -> list:
    def fetch():
        return [t["traceID"] for t in stack.jaeger_traces("olist-shop-api", limit=50) for s in t["spans"]
                if s["attributes"].get("olist.request_id") == request_id]
    return stack.eventually(fetch, 60)


def filled() -> bool:
    try:
        test_queries_filled()
    except AssertionError:
        return False
    return True


def prepare(stack: ObsStack) -> None:
    import httpx

    api = f"http://127.0.0.1:{stack.project.port('api', 8000)}"
    with httpx.Client(trust_env=False, timeout=10) as client:
        for rid in ("chk-7", "chk-77", "chk-7b"):
            assert client.get(f"{api}/orders/{rid}-order", headers={"X-Request-ID": rid}).status_code == 404
        assert client.post(f"{api}/jobs/recompute", headers={"X-Request-ID": "chk-job"}).status_code == 202
        assert stack.loki_query('{service_name="olist-shop-worker"} |= "job done"', timeout=60), "Worker chưa xử lý job"
        stopped = stack.project.run("stop", "redis")
        assert stopped.returncode == 0, stopped.stderr
        for i in range(ERRORS):
            assert client.get(f"{api}/readyz", headers={"X-Request-ID": f"chk-ready-{i}"}).status_code == 503

    def ingested():
        result = stack.loki_query('{service_name="olist-shop-api"} |= "chk-ready-" | json | status >= 500', since=900, limit=50)
        return sum(len(s.get("values") or []) for s in result) >= ERRORS

    assert stack.eventually(ingested, 60), "Loki chưa nhận đủ log 503 của /readyz"


@pytest.fixture(scope="module")
def olist(tmp_path_factory):
    if not filled():
        yield None
        return
    for image in (testkit.KUBE_IMAGES["postgres"], testkit.KUBE_IMAGES["redis"], "python:3.12.16-slim-trixie"):
        ex.require_image(image)
    with DockerLab() as lab:
        try:
            stack = ObsStack(lab, project=olist_project(tmp_path_factory.mktemp("i02")))
            prepare(stack)
        except (pytest.fail.Exception, AssertionError) as error:
            yield str(error)
            return
        yield stack


def ready(olist) -> ObsStack:
    test_queries_filled()
    if isinstance(olist, str):
        pytest.fail(f"Không dựng được stack hay dữ liệu cho bài: {olist}")
    return olist


def test_request_logs_match_exact_request_id(olist):
    stack = ready(olist)
    data = queries()
    found = lines_of(query_loki(stack, data, "request_logs", request_id="chk-7"))
    assert found, "request_logs không trả dòng nào cho request_id chk-7"
    services = {labels.get("service_name") for labels, _ in found}
    assert services == {"olist-shop-api"}, f"request_logs chỉ lấy log của API, đang có {services}"
    ids = {parse(line).get("request_id") for _, line in found}
    assert ids == {"chk-7"}, f"request_logs với chk-7 trả cả log của request khác: {sorted(map(str, ids))}"


def test_trace_id_of_request_leads_to_jaeger_trace(olist):
    stack = ready(olist)
    data = queries()
    found = [line.strip() for _, line in lines_of(query_loki(stack, data, "trace_id_of_request", request_id="chk-77"))]
    assert found, "trace_id_of_request không trả dòng nào cho chk-77"
    assert all(TRACE_ID.match(line) for line in found), f"Mỗi dòng phải chỉ là một trace_id 32 ký tự hex, đang có: {found[:3]}"
    assert len(set(found)) == 1, f"Một request có đúng một trace, query trả {len(set(found))} trace_id khác nhau"
    assert found[0] in server_trace(stack, "chk-77"), "trace_id tìm được không phải trace của request chk-77 trong Jaeger"


def test_follow_job_from_api_log_to_worker_log(olist):
    stack = ready(olist)
    data = queries()
    trace = [line.strip() for _, line in lines_of(query_loki(stack, data, "trace_id_of_request", request_id="chk-job"))]
    assert len(set(trace)) == 1 and TRACE_ID.match(trace[0]), f"trace_id_of_request với chk-job phải ra đúng một trace_id: {trace[:3]}"
    found = lines_of(query_loki(stack, data, "worker_logs_of_trace", trace_id=trace[0]))
    assert found, "worker_logs_of_trace không thấy log nào của worker trong trace của job"
    assert {labels.get("service_name") for labels, _ in found} == {"olist-shop-worker"}, "worker_logs_of_trace chỉ lấy log của worker"
    events = [parse(line) for _, line in found]
    assert all(e.get("trace_id") == trace[0] for e in events), "worker_logs_of_trace trả cả log của trace khác"
    assert any(e.get("msg") == "job done" for e in events), "Phải thấy dòng 'job done' của worker"


def test_errors_by_path(olist):
    stack = ready(olist)
    data = queries()
    result = query_loki(stack, data, "errors_by_path")
    peaks = {}
    for series in result:
        labels = series.get("metric") or {}
        assert set(labels) <= {"path"}, f"errors_by_path chỉ còn nhãn path, đang có {sorted(labels)}"
        peaks[labels.get("path")] = max(float(v) for _, v in series.get("values") or [("", "0")])
    assert peaks.get("/readyz") == ERRORS, f"/readyz trả 503 đúng {ERRORS} lần, query đếm được {peaks.get('/readyz')}"
    assert "/orders/{order_id}" not in peaks, "Request 404 không phải lỗi 5xx"
