"""Phần dùng chung của M06 và M07: chart Olist Shop, render offline, phép kiểm Pod Security restricted, gọi HTTP/TCP từ một
pod của lab."""

import json
import subprocess
from pathlib import Path

from testkit import HELM_MIN_VERSION, Exercise, KubeLab, run_sandboxed

DEPS = Path(__file__).parent / "fixtures" / "k8s-deps.yaml"
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


def helm_offline(chart: Path, home: Path, *args) -> subprocess.CompletedProcess:
    Exercise.require_tool("helm", HELM_MIN_VERSION)
    home.mkdir(parents=True, exist_ok=True)
    env = {"HELM_CACHE_HOME": str(home / "cache"), "HELM_CONFIG_HOME": str(home / "config"),
           "HELM_DATA_HOME": str(home / "data"), "KUBECONFIG": "/dev/null"}
    return run_sandboxed(["helm", *args], writable=[home], readonly=[chart], cwd=home, env=env, timeout=60)


def meta_name(doc: dict) -> str:
    return str((doc.get("metadata") or {}).get("name", ""))


def pod_spec(doc: dict) -> dict:
    return ((doc.get("spec") or {}).get("template") or {}).get("spec") or {}


def restricted_gaps(docs) -> list[str]:
    gaps = []
    for doc in docs:
        if doc.get("kind") not in ("Deployment", "StatefulSet", "DaemonSet", "Job", "Pod"):
            continue
        spec = (doc.get("spec") or {}) if doc["kind"] == "Pod" else pod_spec(doc)
        name = f"{doc['kind']} {meta_name(doc) or '(không tên)'}"
        pod = spec.get("securityContext") or {}
        if pod.get("runAsNonRoot") is not True:
            gaps.append(f"{name}: securityContext.runAsNonRoot: true")
        if (pod.get("seccompProfile") or {}).get("type") != "RuntimeDefault":
            gaps.append(f"{name}: seccompProfile RuntimeDefault")
        for container in (spec.get("initContainers") or []) + (spec.get("containers") or []):
            context = container.get("securityContext") or {}
            where = f"{name}, container {container.get('name') or '(không tên)'}"
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


def get_json(lab: KubeLab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def call(lab: KubeLab, deployment: str, *targets: str) -> dict:
    result = lab.kubectl("exec", f"deployment/{deployment}", "--", "python", "-c", CALL, "-", *targets, check=False, timeout=120)
    assert result.returncode == 0, f"Không exec được vào {deployment}: {result.stderr[-400:]}"
    return json.loads(result.stdout)
