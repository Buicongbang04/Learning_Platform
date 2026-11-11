import shutil
from pathlib import Path

import testkit
from testkit import DockerLab, Exercise, ObsStack

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
APP = testkit.ROOT / "tracks" / "devops" / "sample-app"
CONFIG = "observability/otel-collector/config.yaml"
ORDERS = 40
LIMIT = 20
SERIES = 'traces_span_metrics_calls_total{service_name="olist-shop-api"}'
ORDER_404 = ('sum(traces_span_metrics_calls_total{service_name="olist-shop-api", span_name="GET /orders/{order_id}", '
             'http_request_method="GET", http_response_status_code="404"})')


def olist_project(tmp_path: Path, config: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(APP / "olist_shop", project / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(APP / "requirements.txt", project)
    shutil.copy(testkit.KUBE_OLIST_DOCKERFILE, project / "Dockerfile")
    shutil.copy(FIXTURES / "compose.yaml", project / "compose.yaml")
    folder = project / "observability" / "otel-collector"
    folder.mkdir(parents=True)
    shutil.copy(config, folder / "config.yaml")
    return project


def run_traffic(tmp_path: Path, config: Path) -> dict:
    for image in (testkit.KUBE_IMAGES["postgres"], testkit.KUBE_IMAGES["redis"], "python:3.12.16-slim-trixie"):
        ex.require_image(image)
    import httpx

    with DockerLab() as lab:
        stack = ObsStack(lab, project=olist_project(tmp_path, config))
        api = f"http://127.0.0.1:{stack.project.port('api', 8000)}"
        with httpx.Client(trust_env=False, timeout=10) as client:
            for i in range(ORDERS):
                client.get(f"{api}/orders/i03-{i:03d}")
            client.get(f"{api}/stats/revenue-by-state")
        total = stack.eventually(lambda: [r for r in stack.prom_query(ORDER_404) if float(r["value"][1]) >= ORDERS], 90)
        series = stack.prom_query(SERIES)
        traces = stack.eventually(lambda: [t for t in stack.jaeger_traces("olist-shop-api")
                                           if any(s["attributes"].get("db.system.name") == "postgresql" for s in t["spans"])], 30)
        return {"total": total, "series": [s["metric"] for s in series], "traces": traces}


def leaked(series: list[dict]) -> list[str]:
    return sorted({f"{k}={v}" for metric in series for k, v in metric.items() if "i03-" in v})


def test_span_metrics_stay_bounded(tmp_path):
    result = run_traffic(tmp_path, ex.path(CONFIG))
    assert result["total"], (f"Sau {ORDERS} request GET /orders/..., Prometheus phải có tổng {ORDERS} lời gọi trong "
                             f"traces_span_metrics_calls_total theo span_name, http_request_method=\"GET\" và http_response_status_code=\"404\"")
    count, per_request = len(result["series"]), bool(leaked(result["series"]))
    assert count <= LIMIT, (f"{count} series spanmetrics cho olist-shop-api sau {ORDERS} request; "
                            f"số series phải không phụ thuộc số request (tối đa {LIMIT})")
    assert not per_request, "Series spanmetrics vẫn khác nhau theo từng request"
    assert result["traces"], "Trace kèm span DB vẫn phải tới Jaeger"


def test_starter_config_reproduces_symptom(tmp_path):
    result = run_traffic(tmp_path, FIXTURES / "incident" / "config.yaml")
    assert result["total"], "Cấu hình gốc vẫn phải sinh spanmetrics"
    count = len(result["series"])
    assert count > ORDERS, f"Cấu hình gốc phải tái hiện triệu chứng: số series tăng theo số request, có {count}"
