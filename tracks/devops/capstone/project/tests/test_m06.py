"""M06: chart/olist-shop (Helm chart cho api và worker) cài lên cluster kind devops-lab: HPA, PDB, NetworkPolicy, RBAC,
HTTPRoute qua Gateway dùng chung. Hợp đồng đầy đủ ở capstone/milestones/m06-kubernetes-helm.md."""

import json
import subprocess
import time
from pathlib import Path

import pytest
import yaml

from olist_stack import missing
from testkit import HELM_MIN_VERSION, KUBE_GATEWAY_SERVICE, KUBE_IMAGES, Exercise, KubeLab, run_sandboxed

DOC = "m06-kubernetes-helm.md"
DEPS = Path(__file__).parent / "fixtures" / "k8s-deps.yaml"
RELEASE = "shop"
API, WORKER = f"{RELEASE}-api", f"{RELEASE}-worker"
CONFIG = f"{RELEASE}-config"
ONCALL = f"{RELEASE}-oncall"
ONCALL_GROUP = "olist:oncall"
SELECTOR = {"app.kubernetes.io/name": "olist-shop", "app.kubernetes.io/instance": RELEASE}
REQUIRED = {("Deployment", API), ("Deployment", WORKER), ("Service", API), ("ConfigMap", CONFIG), ("ServiceAccount", API),
            ("ServiceAccount", WORKER), ("HorizontalPodAutoscaler", API), ("PodDisruptionBudget", API),
            ("HTTPRoute", API), ("Role", ONCALL), ("RoleBinding", ONCALL)}
ONCALL_ALLOWED = [
    ("get", "pods", None), ("list", "pods", None), ("watch", "pods", None), ("get", "pods", "log"), ("list", "events", None),
    ("get", "deployments.apps", None), ("list", "deployments.apps", None), ("list", "replicasets.apps", None),
    ("patch", "deployments.apps", "scale"), ("get", "horizontalpodautoscalers.autoscaling", None),
]
ONCALL_DENIED = [
    ("get", "secrets", None), ("list", "secrets", None), ("create", "pods", "exec"), ("create", "pods", "portforward"),
    ("delete", "pods", None), ("create", "pods", None), ("patch", "deployments.apps", None), ("delete", "deployments.apps", None),
    ("patch", "horizontalpodautoscalers.autoscaling", None), ("create", "roles.rbac.authorization.k8s.io", None),
    ("create", "rolebindings.rbac.authorization.k8s.io", None), ("patch", "configmaps", None),
]
WORKLOAD_DENIED = [("get", "secrets"), ("list", "pods"), ("get", "configmaps"), ("list", "services"), ("create", "pods")]
HPA_WAIT = 180
SCALE_WAIT = 120
CALL = r"""
import json, socket, sys, urllib.error, urllib.request
out = {}
for target in sys.argv[2:]:
    method, _, rest = target.partition(" ")
    try:
        if method == "TCP":
            host, port = rest.rsplit(":", 1)
            socket.create_connection((host, int(port)), timeout=3).close()
            out[target] = "ok"
            continue
        url, _, host = rest.partition("|")
        request = urllib.request.Request("http://" + url, method=method, headers={"Host": host} if host else {})
        with urllib.request.urlopen(request, timeout=5) as answer:
            out[target] = "ok %d %s" % (answer.status, answer.read().decode()[:200])
    except urllib.error.HTTPError as error:
        out[target] = "http %d" % error.code
    except Exception as error:
        out[target] = "chan " + type(error).__name__
print(json.dumps(out))
"""


def chart_path(project_root: Path) -> Path:
    return project_root / "chart" / "olist-shop"


def require_chart(project_root: Path) -> Path:
    chart = chart_path(project_root)
    if not (chart / "Chart.yaml").is_file():
        pytest.fail(missing(chart / "Chart.yaml", DOC), pytrace=False)
    return chart


def helm_offline(chart: Path, home: Path, *args) -> subprocess.CompletedProcess:
    Exercise.require_tool("helm", HELM_MIN_VERSION)
    home.mkdir(parents=True, exist_ok=True)
    env = {"HELM_CACHE_HOME": str(home / "cache"), "HELM_CONFIG_HOME": str(home / "config"),
           "HELM_DATA_HOME": str(home / "data"), "KUBECONFIG": "/dev/null"}
    return run_sandboxed(["helm", *args], writable=[home], readonly=[chart], cwd=home, env=env, timeout=60)


def render(chart: Path, home: Path, *args) -> list[dict]:
    result = helm_offline(chart, home, "template", RELEASE, str(chart), "--set", "route.host=shop.olist.test", *args)
    assert result.returncode == 0, f"helm template lỗi:\n{result.stderr[-1500:]}"
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def meta_name(doc: dict) -> str:
    return str((doc.get("metadata") or {}).get("name", ""))


def find(docs, kind, name) -> dict:
    found = [d for d in docs if d.get("kind") == kind and meta_name(d) == name]
    assert found, f"helm template không có {kind} {name}; có {sorted((str(d.get('kind')), meta_name(d)) for d in docs)}"
    return found[0]


def pod_spec(doc: dict) -> dict:
    return ((doc.get("spec") or {}).get("template") or {}).get("spec") or {}


def container(doc: dict, name: str) -> dict:
    found = [c for c in pod_spec(doc).get("containers") or [] if c.get("name") == name]
    assert found, f"{meta_name(doc)}: cần container tên {name}, có {[c.get('name') for c in pod_spec(doc).get('containers') or []]}"
    return found[0]


def job_id_of(answer: str) -> str | None:
    """`job_id` trong body của câu trả lời `ok 202 <json>` do script CALL in ra; None khi body không phải JSON có job_id."""
    try:
        body = json.loads(answer.split(" ", 2)[2])
    except (IndexError, ValueError):
        return None
    return body.get("job_id") if isinstance(body, dict) else None


def restricted_gaps(docs) -> list[str]:
    gaps = []
    for doc in docs:
        if doc.get("kind") not in ("Deployment", "StatefulSet", "DaemonSet", "Job", "Pod"):
            continue
        spec = doc["spec"] if doc["kind"] == "Pod" else pod_spec(doc)
        name = f"{doc['kind']} {doc['metadata']['name']}"
        pod = spec.get("securityContext") or {}
        if pod.get("runAsNonRoot") is not True:
            gaps.append(f"{name}: securityContext.runAsNonRoot: true")
        if (pod.get("seccompProfile") or {}).get("type") != "RuntimeDefault":
            gaps.append(f"{name}: seccompProfile RuntimeDefault")
        for container in spec.get("initContainers", []) + spec.get("containers", []):
            context = container.get("securityContext") or {}
            where = f"{name}, container {container['name']}"
            if context.get("allowPrivilegeEscalation") is not False:
                gaps.append(f"{where}: allowPrivilegeEscalation: false")
            if (context.get("capabilities") or {}).get("drop") != ["ALL"]:
                gaps.append(f"{where}: capabilities.drop [ALL]")
            if context.get("readOnlyRootFilesystem") is not True:
                gaps.append(f"{where}: readOnlyRootFilesystem: true")
            resources = container.get("resources") or {}
            if not (resources.get("requests") or {}).get("cpu") or not (resources.get("requests") or {}).get("memory"):
                gaps.append(f"{where}: resources.requests cpu và memory")
            if not (resources.get("limits") or {}).get("memory"):
                gaps.append(f"{where}: resources.limits.memory")
    return gaps


def test_m06_lint_strict(project_root, tmp_path):
    chart = require_chart(project_root)
    result = helm_offline(chart, tmp_path, "lint", "--strict", str(chart), "--set", "route.host=shop.olist.test")
    assert result.returncode == 0, result.stdout[-1500:] + result.stderr[-500:]


def test_m06_render_objects(project_root, tmp_path):
    docs = render(require_chart(project_root), tmp_path)
    kinds = {(d.get("kind"), meta_name(d)) for d in docs}
    assert REQUIRED <= kinds, f"Chart thiếu {sorted(REQUIRED - kinds)}"
    assert not [d for d in docs if d["kind"] == "Secret"], "Chart không tạo Secret: DATABASE_URL đến từ Secret olist-db có sẵn"
    assert not [d for d in docs if d["kind"] in ("ClusterRole", "ClusterRoleBinding", "Namespace")], (
        "Chart chỉ chứa object trong namespace của release")


def test_m06_labels_and_selectors(project_root, tmp_path):
    docs = render(require_chart(project_root), tmp_path)
    for doc in docs:
        labels = (doc.get("metadata") or {}).get("labels") or {}
        for key, value in (*SELECTOR.items(), ("app.kubernetes.io/managed-by", "Helm"), ("helm.sh/chart", "olist-shop-0.1.0")):
            assert labels.get(key) == value, f"{doc.get('kind')} {meta_name(doc)}: nhãn {key} phải là {value}"
    for name, component in ((API, "api"), (WORKER, "worker")):
        selector = ((find(docs, "Deployment", name).get("spec") or {}).get("selector") or {}).get("matchLabels")
        assert selector == {**SELECTOR, "app.kubernetes.io/component": component}, (
            f"{name}: selector chỉ gồm name, instance, component (selector bất biến sau lần cài đầu): {selector}")
    assert find(docs, "Service", API)["spec"]["selector"] == {**SELECTOR, "app.kubernetes.io/component": "api"}


def test_m06_values_drive_render(project_root, tmp_path):
    chart = require_chart(project_root)
    docs = render(chart, tmp_path, "--set", "image.tag=1.1")
    for name in (API, WORKER):
        images = [c["image"] for c in pod_spec(find(docs, "Deployment", name))["containers"]]
        assert images == ["devops-track/olist-shop:1.1"], f"{name}: image phải lấy từ image.repository và image.tag: {images}"
    assert find(docs, "ConfigMap", CONFIG)["data"].get("APP_VERSION") == "1.1", "APP_VERSION đi theo tag của image"
    default = render(chart, tmp_path)
    for name in (API, WORKER):
        images = [c["image"] for c in pod_spec(find(default, "Deployment", name))["containers"]]
        assert images == ["devops-track/olist-shop:1.0"], f"{name}: mặc định dùng appVersion 1.0 làm tag: {images}"
    route = find(render(chart, tmp_path, "--set", "route.host=demo.olist.test"), "HTTPRoute", API)
    assert route["spec"].get("hostnames") == ["demo.olist.test"], "hostnames của HTTPRoute lấy từ route.host"
    assert route["spec"].get("parentRefs") == [{"name": "public", "namespace": "devops-gateway"}], route["spec"].get("parentRefs")


def test_m06_config_change_rolls_both(project_root, tmp_path):
    chart = require_chart(project_root)
    before = render(chart, tmp_path)
    after = render(chart, tmp_path, "--set", "config.logLevel=DEBUG")
    assert find(after, "ConfigMap", CONFIG)["data"].get("LOG_LEVEL") == "DEBUG"
    for name in (API, WORKER):
        old = (find(before, "Deployment", name)["spec"]["template"]["metadata"].get("annotations") or {}).get("checksum/config")
        new = (find(after, "Deployment", name)["spec"]["template"]["metadata"].get("annotations") or {}).get("checksum/config")
        assert old and old != new, f"{name}: pod template cần annotation checksum/config đổi theo ConfigMap"


def test_m06_workloads_hardened(project_root, tmp_path):
    docs = render(require_chart(project_root), tmp_path)
    gaps = restricted_gaps(docs)
    for name, account, component in ((API, API, "api"), (WORKER, WORKER, "worker")):
        spec = pod_spec(find(docs, "Deployment", name))
        if spec.get("serviceAccountName") != account:
            gaps.append(f"{name}: serviceAccountName phải là {account} (không dùng default)")
        if spec.get("automountServiceAccountToken") is not False:
            gaps.append(f"{name}: automountServiceAccountToken: false (app không gọi API server)")
        main = container(find(docs, "Deployment", name), component)
        refs = [e["valueFrom"]["secretKeyRef"] for e in main.get("env") or [] if "secretKeyRef" in (e.get("valueFrom") or {})]
        if {"name": "olist-db", "key": "DATABASE_URL"} not in refs:
            gaps.append(f"{name}: DATABASE_URL lấy từ secretKeyRef olist-db/DATABASE_URL")
    for account in (API, WORKER):
        if find(docs, "ServiceAccount", account).get("automountServiceAccountToken") is not False:
            gaps.append(f"ServiceAccount {account}: automountServiceAccountToken: false")
    api = container(find(docs, "Deployment", API), "api")
    if (api.get("readinessProbe") or {}).get("httpGet", {}).get("path") != "/readyz":
        gaps.append(f"{API}: readinessProbe httpGet /readyz")
    if (api.get("livenessProbe") or {}).get("httpGet", {}).get("path") != "/healthz":
        gaps.append(f"{API}: livenessProbe httpGet /healthz")
    worker = pod_spec(find(docs, "Deployment", WORKER))
    if not container(find(docs, "Deployment", WORKER), "worker").get("livenessProbe"):
        gaps.append(f"{WORKER}: cần livenessProbe (gợi ý: metrics ở cổng 9101)")
    if (worker.get("terminationGracePeriodSeconds") or 30) < 10:
        gaps.append(f"{WORKER}: terminationGracePeriodSeconds từ 10 trở lên")
    assert not gaps, "\n".join(gaps)


def test_m06_autoscaling_and_disruption(project_root, tmp_path):
    docs = render(require_chart(project_root), tmp_path)
    found = []
    if "replicas" in find(docs, "Deployment", API)["spec"]:
        found.append(f"{API}: bỏ spec.replicas khi HPA quản số replica (mỗi lần helm upgrade sẽ kéo replica về con số này)")
    hpa = find(docs, "HorizontalPodAutoscaler", API)
    spec = hpa["spec"]
    if hpa.get("apiVersion") != "autoscaling/v2":
        found.append("HPA dùng autoscaling/v2")
    if spec.get("scaleTargetRef") != {"apiVersion": "apps/v1", "kind": "Deployment", "name": API}:
        found.append(f"HPA trỏ tới Deployment {API}: {spec.get('scaleTargetRef')}")
    if (spec.get("minReplicas"), spec.get("maxReplicas")) != (2, 5):
        found.append(f"HPA minReplicas 2, maxReplicas 5: {(spec.get('minReplicas'), spec.get('maxReplicas'))}")
    cpu = [m["resource"]["target"] for m in spec.get("metrics") or [] if m.get("type") == "Resource" and m["resource"]["name"] == "cpu"]
    if cpu != [{"type": "Utilization", "averageUtilization": 70}]:
        found.append(f"HPA một metric CPU Utilization 70%: {cpu}")
    pdb = find(docs, "PodDisruptionBudget", API)["spec"]
    if pdb.get("minAvailable") != 1 or pdb.get("selector", {}).get("matchLabels") != {**SELECTOR, "app.kubernetes.io/component": "api"}:
        found.append(f"PDB {API}: minAvailable 1, selector đúng pod api: {pdb}")
    spread = pod_spec(find(docs, "Deployment", API)).get("topologySpreadConstraints") or []
    if not any(c.get("topologyKey") == "kubernetes.io/hostname" and c.get("whenUnsatisfiable") == "DoNotSchedule"
               and c.get("maxSkew") == 1 for c in spread):
        found.append(f"{API}: topologySpreadConstraints maxSkew 1 theo kubernetes.io/hostname, DoNotSchedule")
    assert not found, "\n".join(found)


class Installed:
    def __init__(self, lab: KubeLab | None = None, install=None, error: str = "") -> None:
        self.lab = lab
        self.install = install
        self.error = error
        self.hpa: tuple | None = None

    def require(self) -> KubeLab:
        if self.error:
            pytest.fail(self.error, pytrace=False)
        if self.install.returncode != 0:
            pytest.fail(f"helm install lỗi:\n{self.install.stderr[-2000:]}", pytrace=False)
        return self.lab


def get_json(lab: KubeLab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


@pytest.fixture(scope="module")
def installed(project_root, tmp_path_factory):
    chart = chart_path(project_root)
    if not (chart / "Chart.yaml").is_file():
        yield Installed(error=missing(chart / "Chart.yaml", DOC))
        return
    Exercise.require_cluster()
    Exercise.require_gateway()
    Exercise.require_metrics()
    Exercise.require_tool("helm", HELM_MIN_VERSION)
    Exercise.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    rendered = helm_offline(chart, tmp_path_factory.mktemp("render"), "template", RELEASE, str(chart),
                            "--set", "route.host=shop.olist.test")
    gaps = restricted_gaps([d for d in yaml.safe_load_all(rendered.stdout) if d]) if rendered.returncode == 0 else [
        f"helm template lỗi: {rendered.stderr[-800:]}"]
    if gaps:
        yield Installed(error="Không cài (khỏi chờ hết giờ): chart chưa render được hay pod chưa đạt Pod Security restricted:\n"
                              + "\n".join(gaps))
        return
    with KubeLab(pod_security="restricted") as lab:
        try:
            lab.apply_learner(DEPS)
            for target in ("deployment/postgres", "deployment/redis", "deployment/probe"):
                lab.kubectl("rollout", "status", target, "--timeout=180s", timeout=200)
        except pytest.fail.Exception as error:
            yield Installed(error=f"Không dựng được Postgres, Redis, probe của test (không phải lỗi chart):\n{error}")
            return
        try:
            install = lab.helm_install(RELEASE, chart, "--set", f"route.host={lab.hostname}", "--wait", "--timeout", "240s",
                                       check=False)
        except pytest.fail.Exception as error:
            install = subprocess.CompletedProcess([], 1, "", str(error))
        deadline = time.monotonic() + SCALE_WAIT
        while install.returncode == 0 and time.monotonic() < deadline:
            if ((get_json(lab, "deployment", API) or {}).get("status", {}).get("readyReplicas") or 0) >= 2:
                break
            time.sleep(3)
        yield Installed(lab, install)


def call(lab: KubeLab, deployment: str, *targets: str) -> dict:
    result = lab.kubectl("exec", f"deployment/{deployment}", "--", "python", "-c", CALL, "-", *targets, check=False, timeout=120)
    assert result.returncode == 0, f"Không exec được vào {deployment}: {result.stderr[-400:]}"
    return json.loads(result.stdout)


def eventually(lab: KubeLab, deployment: str, target: str, ok, timeout: float = 60) -> str:
    deadline = time.monotonic() + timeout
    answer = ""
    while time.monotonic() < deadline:
        answer = call(lab, deployment, target)[target]
        if ok(answer):
            return answer
        time.sleep(2)
    return answer


def pod_ips(lab: KubeLab, component: str) -> list[str]:
    pods = get_json(lab, "pods", "-l", f"app.kubernetes.io/instance={RELEASE},app.kubernetes.io/component={component}") or {}
    return [p["status"].get("podIP") for p in pods.get("items", []) if p["status"].get("podIP")]


def test_m06_release_ready(installed):
    lab = installed.require()
    for name, want in ((API, 2), (WORKER, 1)):
        ready = (get_json(lab, "deployment", name) or {}).get("status", {}).get("readyReplicas") or 0
        assert ready >= want, f"Deployment {name} cần ít nhất {want} pod ready, đang {ready}"


def test_m06_api_spread_across_nodes(installed):
    lab = installed.require()
    pods = get_json(lab, "pods", "-l", f"app.kubernetes.io/instance={RELEASE},app.kubernetes.io/component=api") or {}
    nodes = [p["spec"].get("nodeName") for p in pods.get("items", []) if p["status"].get("phase") == "Running"]
    assert len(nodes) >= 2 and len(set(nodes)) == len(nodes), f"Pod api phải nằm trên các node khác nhau: {nodes}"


def test_m06_served_through_gateway(installed):
    lab = installed.require()
    host = lab.hostname
    health = eventually(lab, "probe", f"GET {KUBE_GATEWAY_SERVICE}/healthz|{host}", lambda a: a.startswith("ok 200"), 90)
    assert health.startswith("ok 200") and '"version":"1.0"' in health.replace(" ", ""), (
        f"GET /healthz qua Gateway với Host {host} phải 200 và version 1.0: {health}")
    ready = call(lab, "probe", f"GET {KUBE_GATEWAY_SERVICE}/readyz|{host}")
    assert list(ready.values())[0].startswith("ok 200"), f"/readyz qua Gateway: {ready}"
    other = call(lab, "probe", f"GET {KUBE_GATEWAY_SERVICE}/healthz|other.{host}x")
    assert not list(other.values())[0].startswith("ok"), f"Host khác không được tới api: {other}"
    job = call(lab, "probe", f"POST {KUBE_GATEWAY_SERVICE}/jobs/recompute|{host}")
    answer = list(job.values())[0]
    assert answer.startswith("ok 202"), f"POST /jobs/recompute qua Gateway phải 202: {answer}"
    job_id = job_id_of(answer)
    assert job_id, f"POST /jobs/recompute phải trả JSON có job_id: {answer}"
    deadline = time.monotonic() + 60
    logs = ""
    selector = f"app.kubernetes.io/instance={RELEASE},app.kubernetes.io/component=worker"
    while time.monotonic() < deadline:
        logs = lab.kubectl("logs", "-l", selector, "--prefix", "--tail=200", "--max-log-requests=10", check=False).stdout
        if any(job_id in line and "job done" in line for line in logs.splitlines()):
            return
        time.sleep(2)
    pytest.fail(f"Worker không xử lý job {job_id} trong 60 giây:\n{logs[-1500:]}")


def test_m06_network_policy(installed):
    lab = installed.require()
    api_ip = lab.kubectl("get", "service", API, "-o", "jsonpath={.spec.clusterIP}").stdout.strip()
    kube = lab.kubectl("get", "service", "kubernetes", "-n", "default", "-o", "jsonpath={.spec.clusterIP}",
                       check=False).stdout.strip() or "10.96.0.1"
    worker_ips = pod_ips(lab, "worker")
    assert worker_ips, "Không thấy pod worker"
    direct = call(lab, "probe", f"TCP {api_ip}:8000", f"TCP {worker_ips[0]}:9101")
    assert all(v.startswith("chan") for v in direct.values()), (
        f"Pod khác trong namespace không được gọi thẳng api (chỉ qua Gateway) hay worker: {direct}")
    for name in (API, WORKER):
        reach = call(lab, name, "TCP postgres:5432", "TCP redis:6379")
        assert all(v == "ok" for v in reach.values()), f"{name} phải tới được Postgres, Redis qua tên Service: {reach}"
        blocked = call(lab, name, f"TCP {kube}:443", "TCP 1.1.1.1:443")
        assert all(v.startswith("chan") for v in blocked.values()), f"{name} không được ra API server hay Internet: {blocked}"
    sideways = call(lab, WORKER, f"TCP {api_ip}:8000")
    assert all(v.startswith("chan") for v in sideways.values()), f"worker không cần gọi api: {sideways}"


def test_m06_hpa_reads_metrics(installed):
    lab = installed.require()
    deadline = time.monotonic() + HPA_WAIT
    status = {}
    while time.monotonic() < deadline:
        status = (get_json(lab, "hpa", API) or {}).get("status") or {}
        cpu = [m for m in status.get("currentMetrics") or [] if m.get("type") == "Resource"
               and m["resource"].get("name") == "cpu" and m["resource"]["current"].get("averageUtilization") is not None]
        if cpu:
            break
        time.sleep(5)
    else:
        pytest.fail(f"HPA {API} chưa đọc được CPU sau {HPA_WAIT}s (requests.cpu, metrics-server): {status}")
    assert status.get("currentReplicas") == 2, f"Khi rảnh api chạy minReplicas 2, đang {status.get('currentReplicas')}"
    pdb = (get_json(lab, "pdb", API) or {}).get("status") or {}
    assert pdb.get("expectedPods") == 2 and pdb.get("disruptionsAllowed") == 1, (
        f"PDB {API} phải chọn đúng 2 pod api và cho phép gián đoạn 1: {pdb}")


def test_m06_workload_identities_have_no_api_access(installed):
    lab = installed.require()
    for account in (API, WORKER):
        granted = [f"{verb} {resource}" for verb, resource in WORKLOAD_DENIED if lab.can_i(verb, resource, serviceaccount=account)]
        assert not granted, f"ServiceAccount {account} không cần quyền nào trên API server, đang có: {granted}"
    pods = get_json(lab, "pods", "-l", f"app.kubernetes.io/instance={RELEASE}") or {}
    mounted = [p["metadata"]["name"] for p in pods.get("items", [])
               if any("serviceAccountToken" in json.dumps(v) for v in p["spec"].get("volumes") or [])]
    assert not mounted, f"Pod của release không được mount token ServiceAccount: {mounted}"


@pytest.mark.parametrize("verb,resource,sub", ONCALL_ALLOWED)
def test_m06_oncall_can_operate(installed, verb, resource, sub):
    lab = installed.require()
    assert lab.can_i(verb, resource, subresource=sub, user="oncall-engineer", groups=[ONCALL_GROUP]), (
        f"Nhóm {ONCALL_GROUP} cần {verb} {resource}{'/' + sub if sub else ''} để trực sự cố")


@pytest.mark.parametrize("verb,resource,sub", ONCALL_DENIED)
def test_m06_oncall_least_privilege(installed, verb, resource, sub):
    lab = installed.require()
    assert not lab.can_i(verb, resource, subresource=sub, user="oncall-engineer", groups=[ONCALL_GROUP]), (
        f"Nhóm {ONCALL_GROUP} không được {verb} {resource}{'/' + sub if sub else ''}")


def test_m06_oncall_role_bound_to_group_only(installed):
    lab = installed.require()
    granted = [f"{verb} {resource}{'/' + sub if sub else ''}" for verb, resource, sub in ONCALL_ALLOWED
               if lab.can_i(verb, resource, subresource=sub, user="someone-else", groups=["olist:dev"])]
    assert not granted, f"User ngoài nhóm {ONCALL_GROUP} không được quyền nào của Role {ONCALL}: {granted}"


def test_m06_helpers_tolerate_bad_render():
    """Phép kiểm tĩnh không vỡ với object thiếu metadata/spec và báo đúng container theo tên."""
    docs = [{"kind": "ConfigMap"}, {"kind": "Deployment", "metadata": {"name": API},
                                    "spec": {"template": {"spec": {"containers": [{"name": "sidecar"}, {"name": "api"}]}}}}]
    assert container(find(docs, "Deployment", API), "api") == {"name": "api"}
    with pytest.raises(AssertionError, match="không có Deployment"):
        find(docs, "Deployment", WORKER)
    with pytest.raises(AssertionError, match="cần container tên worker"):
        container(docs[1], "worker")
    assert pod_spec({"kind": "Deployment"}) == {}
    assert job_id_of('ok 202 {"job_id": "abc"}') == "abc"
    assert job_id_of("ok 202 <html>") is None and job_id_of("ok 202") is None
