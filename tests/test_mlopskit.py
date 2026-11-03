import hashlib
import shutil
import subprocess
import time
from pathlib import Path

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


def test_ensure_image_rebuilds_on_dockerfile_change(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit, "docker_ready", lambda: True)
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    sha = hashlib.sha256(b"FROM scratch\n").hexdigest()
    labels = {"img:1": sha}
    builds = []

    def fake_run(cmd, **kw):
        if cmd[1:3] == ["image", "inspect"]:
            tag = cmd[-1]
            if tag not in labels:
                return subprocess.CompletedProcess(cmd, 1, "", "No such image")
            return subprocess.CompletedProcess(cmd, 0, labels[tag] + "\n", "")
        if cmd[1] == "build":
            builds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        raise AssertionError(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert mlopskit._ensure_image("img:1", tmp_path) == "img:1"
    assert builds == [], "nhãn khớp sha Dockerfile thì không build lại"
    (tmp_path / "Dockerfile").write_text("FROM busybox\n")
    mlopskit._ensure_image("img:1", tmp_path)
    new_sha = hashlib.sha256(b"FROM busybox\n").hexdigest()
    assert len(builds) == 1 and f"mlops-dockerfile-sha={new_sha}" in builds[0], builds
    assert not any("mlops-ex=1" in part for part in builds[0])
    labels["img:1"] = "<no value>"
    mlopskit._ensure_image("img:1", tmp_path)
    assert len(builds) == 2, "image cũ không có nhãn thì build lại"
    mlopskit._ensure_image("img:2", tmp_path)
    assert len(builds) == 3 and builds[-1][-2:] == ["img:2", str(tmp_path)]


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


def test_kind_constants():
    assert mlopskit.KIND_CLUSTER == "mlops"
    assert mlopskit.KUBE_CONTEXT == "kind-mlops"


def test_require_kind_skips_without_cluster(monkeypatch):
    monkeypatch.setattr(mlopskit, "_bin", lambda name: None)
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_kind()
    assert "bash setup/mlops/kind/up.sh" in str(info.value)
    assert "13-kubernetes-for-ml" in str(info.value)

    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit, "_kind_clusters", lambda: ["other"])
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_kind()
    assert "bash setup/mlops/kind/up.sh" in str(info.value)
    assert "mlops" in str(info.value)

    monkeypatch.setattr(mlopskit, "_kind_clusters", lambda: ["mlops"])
    monkeypatch.setattr(mlopskit, "_kube_ready", lambda: False)
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_kind()
    assert "bash setup/mlops/kind/up.sh" in str(info.value)


class _FakeRun:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, command, **kwargs):
        self.calls.append((list(command), kwargs))
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, self.stderr)


def test_kubectl_uses_context(monkeypatch):
    fake = _FakeRun(stdout="ok")
    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit.subprocess, "run", fake)
    result = mlopskit.kubectl("get", "pods", namespace="mlops-ex-abc", input="data", timeout=7)
    assert result.stdout == "ok"
    command, kwargs = fake.calls[0]
    assert command[0] == "/fake/kubectl"
    assert command[command.index("--context") + 1] == "kind-mlops"
    assert command[command.index("-n") + 1] == "mlops-ex-abc"
    assert command[-2:] == ["get", "pods"]
    assert kwargs["input"] == "data" and kwargs["timeout"] == 7
    mlopskit.kubectl("get", "ns")
    assert "-n" not in fake.calls[1][0]
    assert "--context" in fake.calls[1][0]


def test_k8s_namespace_removed_on_error(monkeypatch):
    fake = _FakeRun()
    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit, "require_kind", lambda: None)
    monkeypatch.setattr(mlopskit.subprocess, "run", fake)
    holder = []
    with pytest.raises(RuntimeError):
        with mlopskit.k8s_namespace() as ns:
            holder.append(ns)
            raise RuntimeError("boom")
    ns = holder[0]
    assert ns.startswith("mlops-ex-") and len(ns) == len("mlops-ex-") + 8
    created = fake.calls[0]
    assert f"name: {ns}" in created[1]["input"]
    assert '"mlops-ex": "1"' in created[1]["input"]
    assert f'"mlops-ex-run": "{ns.removeprefix("mlops-ex-")}"' in created[1]["input"]
    deletes = [c for c, _ in fake.calls if "delete" in c]
    assert len(deletes) == 1
    assert deletes[0][deletes[0].index("delete") + 1:] == ["namespace", ns, "--wait=false", "--ignore-not-found"]


class _FakePortForward:
    started: list = []

    def __init__(self, command, **kwargs):
        self.command = command
        self.kwargs = kwargs
        self.killed = False
        _FakePortForward.started.append(self)
        local = command[-1].split(":")[0]
        kwargs["stdout"].write(f"Forwarding from 127.0.0.1:{local} -> 8080\n")
        kwargs["stdout"].flush()

    def poll(self):
        return None

    def terminate(self):
        self.killed = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


def test_port_forward_cleans_process(monkeypatch):
    _FakePortForward.started = []

    def no_probe(*args, **kwargs):
        raise AssertionError("port_forward không được kết nối thử vào cổng")

    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit.subprocess, "Popen", _FakePortForward)
    monkeypatch.setattr(mlopskit, "_port_open", no_probe)
    with mlopskit.port_forward("mlops-ex-abc", "svc/api", 8080) as local:
        process = _FakePortForward.started[0]
        command = process.command
        assert command[command.index("--context") + 1] == "kind-mlops"
        assert "svc/api" in command and f"{local}:8080" in command
        assert command[command.index("--address") + 1] == "127.0.0.1"
    assert process.killed
    assert process.kwargs["stdout"] is not subprocess.PIPE
    assert process.kwargs["stderr"] is not subprocess.PIPE


def test_port_forward_fails_when_kubectl_exits(monkeypatch):
    class Dead(_FakePortForward):
        def __init__(self, command, **kwargs):
            self.command, self.kwargs, self.killed = command, kwargs, False
            kwargs["stderr"].write("error: services \"api\" not found\n")
            kwargs["stderr"].flush()

        def poll(self):
            return 1

    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit.subprocess, "Popen", Dead)
    with pytest.raises(pytest.fail.Exception) as info:
        with mlopskit.port_forward("mlops-ex-abc", "svc/api", 8080):
            pass
    assert "not found" in str(info.value)


def _fake_kubectl_factory(calls, *, create_rc=0, wait_rc=1, phase="", describe=None):
    def fake_kubectl(*args, namespace=None, input=None, timeout=120):
        calls.append(args)
        if args[0] == "wait":
            if args[1] == "--for=create":
                return subprocess.CompletedProcess(args, create_rc, "", "" if create_rc == 0 else "NotFound")
            return subprocess.CompletedProcess(args, wait_rc, "", "timed out waiting for the condition")
        if args[0] == "describe":
            if describe is not None:
                return describe(args)
            return subprocess.CompletedProcess(args, 0, "DESCRIBE-OUT", "")
        if args[:2] == ("get", "pods"):
            return subprocess.CompletedProcess(args, 0, "pod-a", "")
        if args[0] == "logs":
            return subprocess.CompletedProcess(args, 0, "LOG-OUT", "")
        if args[0] == "get" and "jsonpath={.status.phase}" in args:
            return subprocess.CompletedProcess(args, 0, phase, "")
        return subprocess.CompletedProcess(args, 0, "", "")
    return fake_kubectl


def test_wait_for_timeout_reports_describe_and_logs(monkeypatch):
    calls = []
    monkeypatch.setattr(mlopskit, "kubectl", _fake_kubectl_factory(calls))
    with pytest.raises(pytest.fail.Exception) as info:
        mlopskit.wait_for("deployment", "api", "Available", "mlops-ex-abc", timeout=2)
    text = str(info.value)
    assert "DESCRIBE-OUT" in text and "LOG-OUT" in text and "Available" in text
    assert calls[0][:2] == ("wait", "--for=create") and "deployment/api" in calls[0]
    waits = [c for c in calls if c[0] == "wait" and c[1] != "--for=create"]
    assert "--for=condition=Available" in waits[0] and "deployment/api" in waits[0]


def test_wait_for_waits_for_creation_first(monkeypatch):
    calls = []
    monkeypatch.setattr(mlopskit, "kubectl", _fake_kubectl_factory(calls, wait_rc=0))
    mlopskit.wait_for("workflow", "wf", "jsonpath={.status.phase}=Succeeded", "mlops-ex-abc", timeout=30)
    assert calls[0][:2] == ("wait", "--for=create")
    assert calls[1][1] == "--for=jsonpath={.status.phase}=Succeeded"

    calls.clear()
    monkeypatch.setattr(mlopskit, "kubectl", _fake_kubectl_factory(calls, create_rc=1))
    with pytest.raises(pytest.fail.Exception) as info:
        mlopskit.wait_for("workflow", "wf", "Ready", "mlops-ex-abc", timeout=3)
    assert "không xuất hiện" in str(info.value)


def test_wait_for_fail_on_phase_fails_fast(monkeypatch):
    calls = []
    monkeypatch.setattr(mlopskit, "kubectl", _fake_kubectl_factory(calls, phase="Failed"))
    started = time.monotonic()
    with pytest.raises(pytest.fail.Exception) as info:
        mlopskit.wait_for("workflow", "wf", "jsonpath={.status.phase}=Succeeded", "mlops-ex-abc", timeout=300,
                          fail_on=("Failed", "Error"))
    assert time.monotonic() - started < 10
    assert "phase Failed" in str(info.value)


def test_wait_for_diagnose_errors_do_not_hide_reason(monkeypatch):
    calls = []

    def describe(args):
        pytest.fail("kubectl describe quá 15 giây", pytrace=False)

    monkeypatch.setattr(mlopskit, "kubectl", _fake_kubectl_factory(calls, describe=describe))
    with pytest.raises(pytest.fail.Exception) as info:
        mlopskit.wait_for("deployment", "api", "Available", "mlops-ex-abc", timeout=2)
    assert "không đạt condition=Available" in str(info.value)


def test_kind_roundtrip():
    mlopskit.require_kind()
    with mlopskit.k8s_namespace() as ns:
        labels = mlopskit.kubectl("get", "namespace", ns, "-o", "jsonpath={.metadata.labels}").stdout
        assert '"mlops-ex":"1"' in labels and f'"mlops-ex-run":"{ns.removeprefix("mlops-ex-")}"' in labels
        manifest = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: probe\ndata:\n  answer: \"42\"\n"
        assert mlopskit.apply_manifest(manifest, ns).returncode == 0
        got = mlopskit.kubectl("get", "configmap", "probe", "-o", "jsonpath={.data.answer}", namespace=ns)
        assert got.stdout == "42"
        assert mlopskit.leftovers(ns) == [ns]
    phase = mlopskit.kubectl("get", "namespace", ns, "-o", "jsonpath={.status.phase}", "--ignore-not-found").stdout
    assert phase in ("", "Terminating")
    assert mlopskit.leftovers(ns) == []


def test_kserve_and_argo_installed():
    mlopskit.require_kind()
    for crd in ("inferenceservices.serving.kserve.io", "workflows.argoproj.io", "certificates.cert-manager.io"):
        assert mlopskit.kubectl("get", "crd", crd).returncode == 0, crd
    deploy = mlopskit.kubectl("get", "configmap", "inferenceservice-config", "-o", "jsonpath={.data.deploy}",
                              namespace="kserve").stdout
    assert "RawDeployment" in deploy
    for namespace, name in (("cert-manager", "cert-manager-webhook"), ("kserve", "kserve-controller-manager"),
                            ("argo", "workflow-controller"), ("argo", "argo-artifacts")):
        status = mlopskit.kubectl("get", "deployment", name, "-o", "jsonpath={.status.availableReplicas}",
                                  namespace=namespace)
        assert status.stdout == "1", f"{namespace}/{name}: {status.stdout}{status.stderr}"


ARGO_ARTIFACT_WORKFLOW = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: artifact-probe
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: write
            template: write
        - - name: read
            template: read
            arguments:
              artifacts:
                - name: msg
                  from: "{{steps.write.outputs.artifacts.msg}}"
    - name: write
      container:
        image: busybox:1.37
        imagePullPolicy: IfNotPresent
        command: [sh, -c, "echo mlops-artifact > /tmp/msg.txt"]
      outputs:
        artifacts:
          - name: msg
            path: /tmp/msg.txt
    - name: read
      inputs:
        artifacts:
          - name: msg
            path: /tmp/in.txt
      container:
        image: busybox:1.37
        imagePullPolicy: IfNotPresent
        command: [sh, -c, "grep -q mlops-artifact /tmp/in.txt"]
"""


def test_argo_workflow_artifact_and_kind_load():
    mlopskit.require_kind()
    _busybox()
    mlopskit.kind_load("busybox:1.37")
    with mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(ARGO_ARTIFACT_WORKFLOW, ns)
        mlopskit.wait_for("workflow", "artifact-probe", "jsonpath={.status.phase}=Succeeded", ns, timeout=300,
                          fail_on=("Failed", "Error"))


def test_require_cuda_skips_without_gpu(monkeypatch):
    monkeypatch.setattr(mlopskit.shutil, "which", lambda name: None)
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_cuda()
    assert "Không có CUDA" in str(info.value)


def test_gpu_python_command(monkeypatch, tmp_path):
    fake = _FakeRun(stdout="{}")
    monkeypatch.setattr(mlopskit.subprocess, "run", fake)
    monkeypatch.setattr(mlopskit, "_gpu_env_ready", lambda: True)
    monkeypatch.setenv("VIRTUAL_ENV", "/somewhere/.venv")
    mlopskit.gpu_python("print(1)", tmp_path, timeout=9)
    command, kwargs = fake.calls[0]
    assert command[command.index("--project") + 1] == str(mlopskit.ROOT / "setup" / "gpu")
    assert "--no-sync" in command and "--frozen" not in command
    assert command[-4:] == ["python", "-I", "-c", "print(1)"]
    assert kwargs["cwd"] == tmp_path and kwargs["timeout"] == 9
    assert "VIRTUAL_ENV" not in kwargs["env"]


def test_gpu_python_skip_or_run(tmp_path):
    import json

    mlopskit.require_cuda()
    script = (
        "import json, onnxruntime as ort\n"
        "from onnx import helper, TensorProto\n"
        "ort.preload_dlls()\n"
        "x = helper.make_tensor_value_info('x', TensorProto.FLOAT, [2, 2])\n"
        "y = helper.make_tensor_value_info('y', TensorProto.FLOAT, [2, 2])\n"
        "g = helper.make_graph([helper.make_node('Relu', ['x'], ['y'])], 'g', [x], [y])\n"
        "m = helper.make_model(g, opset_imports=[helper.make_opsetid('', 17)])\n"
        "m.ir_version = 9\n"
        "s = ort.InferenceSession(m.SerializeToString(), providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])\n"
        "import numpy as np\n"
        "out = s.run(None, {'x': np.array([[-1, 2], [3, -4]], dtype=np.float32)})[0]\n"
        "print(json.dumps({'providers': s.get_providers(), 'out': out.tolist()}))\n"
    )
    result = mlopskit.gpu_python(script, tmp_path)
    assert result.returncode == 0, result.stderr[-3000:]
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data["providers"][0] == "CUDAExecutionProvider", data
    assert data["out"] == [[0.0, 2.0], [3.0, 0.0]]


def test_k8s_namespace_delete_failure_does_not_mask_error(monkeypatch, capsys):
    calls = []

    def fake_kubectl(*args, namespace=None, input=None, timeout=120):
        calls.append((args, timeout))
        if args[0] == "delete":
            pytest.fail("kubectl delete quá 30 giây", pytrace=False)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(mlopskit, "require_kind", lambda: None)
    monkeypatch.setattr(mlopskit, "kubectl", fake_kubectl)
    with pytest.raises(RuntimeError, match="boom"):
        with mlopskit.k8s_namespace():
            raise RuntimeError("boom")
    delete = [c for c in calls if c[0][0] == "delete"]
    assert delete and delete[0][1] <= 30
    assert "không xoá được namespace" in capsys.readouterr().err


def test_leftovers_reports_stuck_terminating(monkeypatch):
    from datetime import datetime, timedelta, timezone

    old = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fresh = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    listing = (f"default Active \nmlops-ex-aaaa1111 Active \nmlops-ex-bbbb2222 Terminating {old}\n"
               f"mlops-ex-cccc3333 Terminating {fresh}\n")
    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit, "_kind_clusters", lambda **k: ["mlops"])
    monkeypatch.setattr(mlopskit, "kubectl",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, listing, ""))
    assert mlopskit._leftover_namespaces() == ["mlops-ex-aaaa1111", "mlops-ex-bbbb2222"]


def test_leftover_namespaces_best_effort(monkeypatch):
    def hang(*args, **kwargs):
        pytest.fail("kubectl get namespaces quá 10 giây", pytrace=False)

    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit, "_kind_clusters", lambda **k: ["mlops"])
    monkeypatch.setattr(mlopskit, "kubectl", hang)
    assert mlopskit._leftover_namespaces() == []
    monkeypatch.setattr(mlopskit, "_kind_clusters", lambda **k: [])
    assert mlopskit._leftover_namespaces() == []


def test_bin_prefers_pinned_local_copy(monkeypatch, tmp_path):
    pinned = tmp_path / "kubectl"
    pinned.write_text("#!/bin/sh\n")
    pinned.chmod(0o755)
    monkeypatch.setattr(mlopskit, "LOCAL_BIN", tmp_path)
    monkeypatch.setattr(mlopskit.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert mlopskit._bin("kubectl") == str(pinned)
    assert mlopskit._bin("kind") == "/usr/bin/kind"


def test_kind_load_uses_disk_cache_and_cleans(monkeypatch, tmp_path):
    assert mlopskit.KIND_LOAD_DIR.is_relative_to(Path.home())
    seen = {}

    def fake_docker(*args, timeout=60, env=None):
        if args[0] == "save":
            archive = Path(args[args.index("-o") + 1])
            archive.write_bytes(b"tar")
            seen["archive"] = archive
            seen["mode"] = oct(archive.parent.parent.stat().st_mode & 0o777)
        return subprocess.CompletedProcess(args, 0, "amd64\n", "")

    monkeypatch.setattr(mlopskit, "require_kind", lambda: None)
    monkeypatch.setattr(mlopskit, "_bin", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mlopskit, "_docker", fake_docker)
    monkeypatch.setattr(mlopskit, "KIND_LOAD_DIR", tmp_path / "load")
    monkeypatch.setattr(mlopskit.subprocess, "run", _FakeRun())
    mlopskit.kind_load("img:1")
    assert seen["archive"].is_relative_to(tmp_path / "load")
    assert seen["mode"] == "0o700"
    assert not seen["archive"].exists() and list((tmp_path / "load").iterdir()) == []


def test_gpu_env_problem_reports_missing_env(monkeypatch, tmp_path):
    monkeypatch.setattr(mlopskit, "GPU_PROJECT", tmp_path)
    monkeypatch.setattr(mlopskit, "_GPU_ENV_STATE", {})
    assert "Chưa có môi trường setup/gpu" in mlopskit._gpu_env_problem()
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.gpu_python("print(1)", tmp_path)
    assert "uv sync --project setup/gpu" in str(info.value)


PROBE_POD = """
apiVersion: v1
kind: Pod
metadata:
  name: {name}
  labels: {labels}
spec:
  restartPolicy: Never
  containers:
    - name: probe
      image: busybox:1.37
      imagePullPolicy: IfNotPresent
      command: [sh, -c, "wget -q -T 5 -O /dev/null http://argo-artifacts.argo.svc.cluster.local:9000/minio/health/live"]
"""


def test_argo_artifacts_network_policy():
    mlopskit.require_kind()
    _busybox()
    mlopskit.kind_load("busybox:1.37")
    with mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(PROBE_POD.format(name="outsider", labels="{}"), ns)
        mlopskit.apply_manifest(PROBE_POD.format(name="workflow-pod", labels='{"workflows.argoproj.io/workflow": "x"}'), ns)
        mlopskit.wait_for("pod", "workflow-pod", "jsonpath={.status.phase}=Succeeded", ns, timeout=120, fail_on=("Failed",))
        mlopskit.wait_for("pod", "outsider", "jsonpath={.status.phase}=Failed", ns, timeout=120, fail_on=("Succeeded",))
