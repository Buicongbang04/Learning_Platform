import shutil
import subprocess

import pytest

import mlopskit
import testkit


def _docker_image_exists(tag: str) -> bool:
    result = subprocess.run(["docker", "image", "inspect", tag], capture_output=True, text=True)
    return result.returncode == 0


def _need_docker():
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")


def _busybox():
    _need_docker()
    if subprocess.run(["docker", "image", "inspect", "busybox:1.37"], capture_output=True).returncode != 0:
        subprocess.run(["docker", "pull", "busybox:1.37"], capture_output=True, timeout=300)


def test_stack_services_table():
    assert mlopskit.STACK_SERVICES == {
        "postgres": ("MLOPS_PG_PORT", 25433),
        "minio": ("MLOPS_MINIO_PORT", 29000),
        "mlflow": ("MLOPS_MLFLOW_PORT", 25000),
        "prometheus": ("MLOPS_PROMETHEUS_PORT", 29090),
        "alertmanager": ("MLOPS_ALERTMANAGER_PORT", 29093),
        "grafana": ("MLOPS_GRAFANA_PORT", 23000),
        "redis": ("MLOPS_REDIS_PORT", 26390),
    }


def test_stack_port_default(monkeypatch):
    monkeypatch.delenv("MLOPS_MLFLOW_PORT", raising=False)
    assert mlopskit.stack_port("mlflow") == 25000


def test_stack_port_env(monkeypatch):
    monkeypatch.setenv("MLOPS_MLFLOW_PORT", "25999")
    assert mlopskit.stack_port("mlflow") == 25999


def test_require_stack_down_skips(monkeypatch):
    monkeypatch.setenv("MLOPS_MLFLOW_PORT", str(testkit.free_port()))
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_stack("mlflow")
    assert "docker compose -f setup/mlops/compose.yaml up -d --wait" in str(info.value)
    assert "mlflow" in str(info.value)


def test_require_stack_up_passes(monkeypatch):
    import socket

    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        monkeypatch.setenv("MLOPS_MLFLOW_PORT", str(server.getsockname()[1]))
        mlopskit.require_stack("mlflow")


def test_mlflow_local_roundtrip(tmp_path):
    import mlflow

    uri = mlopskit.mlflow_local(tmp_path)
    assert uri.startswith("sqlite:///")
    assert str(tmp_path) in uri
    with mlflow.start_run():
        mlflow.log_metric("mae", 1.0)
    runs = mlflow.search_runs()
    assert len(runs) == 1
    assert runs["metrics.mae"].iloc[0] == 1.0


def test_built_image_removed(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\n")
    with mlopskit.built_image(tmp_path) as tag:
        assert tag.startswith("mlops-ex-") and tag.endswith(":test")
        assert _docker_image_exists(tag)
    assert not _docker_image_exists(tag)


def test_built_image_removed_on_error(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\n")
    holder = []
    with pytest.raises(RuntimeError):
        with mlopskit.built_image(tmp_path) as tag:
            holder.append(tag)
            raise RuntimeError("boom")
    assert not _docker_image_exists(holder[0])


def test_built_image_build_args(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\nARG WHO=x\nENV WHO=$WHO\n")
    with mlopskit.built_image(tmp_path, build_args={"WHO": "mlops"}) as tag:
        out = subprocess.run(["docker", "run", "--rm", tag, "sh", "-c", "echo $WHO"], capture_output=True, text=True)
        assert out.stdout.strip() == "mlops"


def test_image_inspect_helpers(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\n")
    with mlopskit.built_image(tmp_path) as plain:
        assert mlopskit.image_size_bytes(plain) > 1_000_000
        assert mlopskit.image_inspect(plain, "{{.Os}}") == "linux"
        assert not mlopskit.image_has_healthcheck(plain)
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\nHEALTHCHECK CMD true\n")
    with mlopskit.built_image(tmp_path) as checked:
        assert mlopskit.image_has_healthcheck(checked)


def test_image_inspect_missing_image_fails():
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    with pytest.raises(pytest.fail.Exception):
        mlopskit.image_size_bytes("mlops-ex-does-not-exist:none")


def test_built_image_failure_reports_log(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\nRUN exit 3\n")
    with pytest.raises(pytest.fail.Exception):
        with mlopskit.built_image(tmp_path):
            pass


COMPOSE = """services:
  app:
    image: busybox:1.37
    command: sleep 300
"""


def test_compose_roundtrip_and_down(tmp_path):
    _busybox()
    (tmp_path / "compose.yaml").write_text(COMPOSE)
    with mlopskit.compose_project(tmp_path / "compose.yaml") as project:
        assert project.name.startswith("mlops-ex-")
        assert project.exec("app", "echo", "hi").stdout.strip() == "hi"
        assert isinstance(project.logs("app"), str)
        name = project.name
        assert mlopskit.leftovers(name)
    assert mlopskit.leftovers(name) == []


def test_compose_down_on_error(tmp_path):
    _busybox()
    (tmp_path / "compose.yaml").write_text(COMPOSE)
    with pytest.raises(RuntimeError):
        with mlopskit.compose_project(tmp_path / "compose.yaml") as project:
            name = project.name
            raise RuntimeError("boom")
    assert mlopskit.leftovers(name) == []


def test_build_timeout_env(monkeypatch):
    monkeypatch.delenv("MLOPS_BUILD_TIMEOUT", raising=False)
    assert mlopskit.build_timeout() == 1800
    monkeypatch.setenv("MLOPS_BUILD_TIMEOUT", "42")
    assert mlopskit.build_timeout() == 42
    for bad in ("abc", "0", "-5", ""):
        monkeypatch.setenv("MLOPS_BUILD_TIMEOUT", bad)
        assert mlopskit.build_timeout() == 1800


def test_build_timeout_message(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit, "docker_ready", lambda: True)
    monkeypatch.setenv("MLOPS_BUILD_TIMEOUT", "7")
    seen = {}

    def fake_run(cmd, **kw):
        if "build" not in cmd and "up" not in cmd:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        seen["timeout"] = kw["timeout"]
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    for ctx in (
        lambda: mlopskit.built_image(tmp_path),
        lambda: mlopskit.compose_project(tmp_path / "c.yaml"),
    ):
        with pytest.raises(pytest.fail.Exception) as exc:
            with ctx():
                pass
        assert "MLOPS_BUILD_TIMEOUT" in str(exc.value) and "7 giây" in str(exc.value)
        assert "cache" in str(exc.value)
        assert seen["timeout"] == 7


def test_stack_port_new_services(monkeypatch):
    for env in ("MLOPS_PROMETHEUS_PORT", "MLOPS_ALERTMANAGER_PORT", "MLOPS_GRAFANA_PORT", "MLOPS_REDIS_PORT"):
        monkeypatch.delenv(env, raising=False)
    assert mlopskit.stack_port("prometheus") == 29090
    assert mlopskit.stack_port("alertmanager") == 29093
    assert mlopskit.stack_port("grafana") == 23000
    assert mlopskit.stack_port("redis") == 26390


@pytest.mark.parametrize("service,profile", [("prometheus", "monitoring"), ("alertmanager", "monitoring"),
                                              ("grafana", "monitoring"), ("redis", "feast")])
def test_require_stack_profile_hint(monkeypatch, service, profile):
    env = mlopskit.STACK_SERVICES[service][0]
    monkeypatch.setenv(env, str(testkit.free_port()))
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_stack(service)
    assert f"--profile {profile}" in str(info.value)
    assert "setup/mlops/compose.yaml" in str(info.value)


def test_require_stack_core_hint_has_no_profile(monkeypatch):
    monkeypatch.setenv("MLOPS_MLFLOW_PORT", str(testkit.free_port()))
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_stack("mlflow")
    assert "--profile" not in str(info.value)


def _fake_month(tmp_path, monkeypatch, content=b"not a parquet"):
    folder = tmp_path / "nyc-tlc"
    folder.mkdir()
    (folder / "yellow_tripdata_2019-01.parquet").write_bytes(content)
    monkeypatch.setattr(testkit.Exercise, "dataset", staticmethod(lambda name: tmp_path / name))


def test_real_month_checksum_mismatch(tmp_path, monkeypatch):
    _fake_month(tmp_path, monkeypatch)
    with pytest.raises(pytest.fail.Exception) as info:
        mlopskit.real_month("nyc-tlc", "2019-01")
    assert "sha256" in str(info.value)


def test_real_month_accepts_matching_checksum(tmp_path, monkeypatch):
    import hashlib

    _fake_month(tmp_path, monkeypatch, b"abc")
    key = "nyc-tlc/yellow_tripdata_2019-01.parquet"
    monkeypatch.setitem(mlopskit.REAL_SHA256, key, hashlib.sha256(b"abc").hexdigest())
    assert mlopskit.real_month("nyc-tlc", "2019-01").name == "yellow_tripdata_2019-01.parquet"


def test_real_month_unknown_month():
    with pytest.raises(pytest.fail.Exception):
        mlopskit.real_month("nyc-tlc", "2019-13")


def test_real_month_skips_when_missing(monkeypatch):
    def missing(name):
        pytest.skip(f"Chưa tải bộ {name}")

    monkeypatch.setattr(testkit.Exercise, "dataset", staticmethod(missing))
    with pytest.raises(pytest.skip.Exception):
        mlopskit.real_month("nyc-tlc", "2019-01")


def test_real_sha256_table_complete():
    expected = {f"{ds}/yellow_tripdata_{year}-{m:02d}.parquet"
                for ds, year in (("nyc-tlc", 2019), ("nyc-tlc-2020", 2020)) for m in range(1, 13)}
    assert set(mlopskit.REAL_SHA256) == expected
    assert all(len(v) == 64 for v in mlopskit.REAL_SHA256.values())


def test_real_month_real_data_matches_table():
    path = mlopskit.real_month("nyc-tlc", "2019-01")
    assert path.stat().st_size > 1_000_000


def test_promtool_check_config(tmp_path):
    _need_docker()
    (tmp_path / "ok.yml").write_text("global:\n  scrape_interval: 15s\nscrape_configs:\n  - job_name: a\n    static_configs:\n      - targets: ['localhost:9090']\n")
    (tmp_path / "bad.yml").write_text("scrape_configs: [unclosed\n")
    ok = mlopskit.promtool("check", "config", "ok.yml", cwd=tmp_path)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = mlopskit.promtool("check", "config", "bad.yml", cwd=tmp_path)
    assert bad.returncode != 0
    assert "bad.yml" in bad.stdout + bad.stderr or "yaml" in (bad.stdout + bad.stderr).lower()
    assert mlopskit.leftovers("promtool") == []


def test_evidently_python_report(tmp_path):
    _need_docker()
    import json

    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    pd.DataFrame({"x": rng.normal(0, 1, 500)}).to_parquet(tmp_path / "ref.parquet")
    pd.DataFrame({"x": rng.normal(2, 1, 500)}).to_parquet(tmp_path / "cur.parquet")
    script = (
        "import json, pandas as pd, evidently\n"
        "from evidently import Report\n"
        "from evidently.presets import DataDriftPreset\n"
        "r = Report([DataDriftPreset()]).run(pd.read_parquet('cur.parquet'), pd.read_parquet('ref.parquet'))\n"
        "print(json.dumps({'v': evidently.__version__, 'n': len(r.dict()['metrics'])}))\n"
    )
    result = mlopskit.evidently_python(tmp_path, script)
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["v"] == "0.7.23" and out["n"] > 0
    assert mlopskit.leftovers("evidently") == []


def test_evidently_not_in_host_env():
    import importlib.util

    assert importlib.util.find_spec("evidently") is None


def test_amtool_check_config(tmp_path):
    _need_docker()
    (tmp_path / "ok.yml").write_text("route:\n  receiver: oncall\nreceivers:\n  - name: oncall\n")
    (tmp_path / "bad.yml").write_text("route:\n  receiver: missing\nreceivers:\n  - name: oncall\n")
    ok = mlopskit.amtool("check-config", "ok.yml", cwd=tmp_path)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = mlopskit.amtool("check-config", "bad.yml", cwd=tmp_path)
    assert bad.returncode != 0
    assert "missing" in bad.stdout + bad.stderr
    routes = mlopskit.amtool("config", "routes", "test", "--config.file=ok.yml", "severity=critical", cwd=tmp_path)
    assert routes.returncode == 0 and "oncall" in routes.stdout, routes.stdout + routes.stderr
    assert mlopskit.leftovers("amtool") == []


def test_act_run_rejects_container_options_in_args(tmp_path):
    if shutil.which("act") is None:
        pytest.skip("act chưa cài")
    with pytest.raises(ValueError):
        mlopskit.act_run(tmp_path, "--container-options", "--user 1:1")


def test_feast_run_version(tmp_path):
    _need_docker()
    result = mlopskit.feast_run(tmp_path, "version")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0.67.0" in result.stdout + result.stderr


def test_feast_python_json(tmp_path):
    _need_docker()
    result = mlopskit.feast_python(tmp_path, "import json, feast; print(json.dumps({'v': feast.__version__}))")
    assert result.returncode == 0, result.stdout + result.stderr
    import json

    assert json.loads(result.stdout.strip().splitlines()[-1]) == {"v": "0.67.0"}


def test_feast_image_not_labeled_for_cleanup():
    _need_docker()
    tag = mlopskit.feast_image()
    assert tag == mlopskit.FEAST_IMAGE == "mlops-feast:0.67.0"
    assert tag not in mlopskit.leftovers()


WORKFLOW = """name: mlopskit-selftest
on: push
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: python3 -c "print(42)"
"""


def test_act_run_offline(tmp_path):
    _need_docker()
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(WORKFLOW)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    import os

    for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"], ["git", "commit", "-q", "-m", "init"]):
        subprocess.run(cmd, cwd=tmp_path, check=True, env={**os.environ, **env})
    result = mlopskit.act_run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "42" in result.stdout + result.stderr
    assert mlopskit.leftovers("mlopskit-selftest") == []


def test_act_run_skips_without_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(mlopskit.shutil, "which", lambda name: None)
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.act_run(tmp_path)
    assert "08-cicd-for-ml" in str(info.value)


def test_k6_run_smoke(tmp_path):
    _need_docker()
    import http.server
    import json
    import threading

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        script = tmp_path / "smoke.js"
        script.write_text(
            "import http from 'k6/http';\nimport { check } from 'k6';\n"
            "export const options = { vus: 1, iterations: 5 };\n"
            "export default function () {\n  const r = http.get(`${__ENV.TARGET}/`);\n"
            "  check(r, { ok: (x) => x.status === 200 });\n}\n"
        )
        result = mlopskit.k6_run(script, {"TARGET": f"http://127.0.0.1:{server.server_address[1]}"})
        assert result.returncode == 0, result.stdout + result.stderr
        summary = json.loads(result.stdout)
        assert summary["metrics"]["http_reqs"]["count"] == 5
    finally:
        server.shutdown()
    assert mlopskit.leftovers("k6") == []


def test_dvc_sh_runs_in_repo(tmp_path):
    result = mlopskit.dvc_sh(tmp_path, 'echo "$1 $DVC_NO_ANALYTICS"', args=("hi",))
    assert result.stdout.strip() == "hi 1"
    with pytest.raises(AssertionError):
        mlopskit.dvc_sh(tmp_path, "exit 3")
    assert mlopskit.dvc_sh(tmp_path, "exit 3", ok=False).returncode == 3
