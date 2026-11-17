import json
import shutil
import time
from pathlib import Path

import pytest

from testkit import KUBE_GATEWAY_SERVICE, KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
DEPS = Path(__file__).parent / "fixtures" / "deps.yaml"
PLACEHOLDER = "lab.olist.test"
CALL = """
import json, sys, urllib.error, urllib.request
host, path, count, canary = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
seen = {}
for _ in range(count):
    headers = {"Host": host}
    if canary:
        headers["X-Canary"] = canary
    request = urllib.request.Request("http://%s%s" % (sys.argv[5], path), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as answer:
            body = json.load(answer)
            key = body.get("version") or json.dumps(body, sort_keys=True)
    except urllib.error.HTTPError as error:
        key = "http-%d" % error.code
    except Exception as error:
        key = "loi-" + type(error).__name__
    seen[key] = seen.get(key, 0) + 1
print(json.dumps(seen))
"""


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def call(lab, host: str, path: str, count: int, canary: str = "") -> dict:
    result = lab.kubectl("exec", "deployment/api-stable", "--", "python", "-c", CALL, host, path, str(count), canary,
                         KUBE_GATEWAY_SERVICE, check=False, timeout=120)
    return json.loads(result.stdout) if result.returncode == 0 else {"loi-exec": result.stderr[-300:]}


def wait_routed(lab, host: str, timeout: float = 60) -> dict:
    deadline = time.monotonic() + timeout
    seen = {}
    while time.monotonic() < deadline:
        seen = call(lab, host, "/healthz", 1)
        if any(key in ("1.4", "1.5") for key in seen):
            return seen
        time.sleep(2)
    return seen


@pytest.fixture(scope="module")
def routed(tmp_path_factory):
    ex.require_cluster()
    ex.require_gateway()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        lab.apply_learner(DEPS)
        for target in ("deployment/postgres", "deployment/redis"):
            lab.kubectl("rollout", "status", target, "--timeout=180s")
        staged = tmp_path_factory.mktemp("k8s")
        for source in sorted(ex.path("k8s").iterdir()):
            if source.suffix in (".yaml", ".yml"):
                (staged / source.name).write_text(source.read_text(encoding="utf-8").replace(PLACEHOLDER, lab.hostname),
                                                  encoding="utf-8")
        state = {"applied": lab.apply_learner(staged, check=False)}
        state["rollouts"] = {t: lab.kubectl("rollout", "status", t, "--timeout=180s", check=False).returncode
                             for t in ("deployment/api-stable", "deployment/api-canary")}
        state["legacy_first"] = wait_routed(lab, f"legacy.{lab.hostname}")
        state["main_first"] = wait_routed(lab, lab.hostname)
        yield lab, state


def test_manifests_apply(routed):
    _, state = routed
    assert state["applied"].returncode == 0, state["applied"].stderr
    assert state["rollouts"] == {"deployment/api-stable": 0, "deployment/api-canary": 0}


def test_ingress_routes_legacy_host_to_stable(routed):
    lab, _ = routed
    ingress = get_json(lab, "ingress", "olist-legacy")
    assert ingress, "Cần Ingress olist-legacy"
    assert call(lab, f"legacy.{lab.hostname}", "/healthz", 10) == {"1.4": 10}, "Host legacy.<lab> phải luôn tới api-stable"
    readyz = call(lab, f"legacy.{lab.hostname}", "/readyz", 1)
    assert readyz == {json.dumps({"db": "ok", "redis": "ok"}, sort_keys=True): 1}, readyz


def test_httproute_accepted_by_shared_gateway(routed):
    lab, _ = routed
    route = get_json(lab, "httproute", "olist")
    assert route, "Cần HTTPRoute olist"
    parents = route.get("status", {}).get("parents", [])
    accepted = [c for p in parents for c in p.get("conditions", []) if c["type"] == "Accepted"]
    assert accepted and all(c["status"] == "True" for c in accepted), f"Gateway chưa nhận route: {parents}"


def test_httproute_splits_traffic_90_10(routed):
    lab, _ = routed
    seen = call(lab, lab.hostname, "/healthz", 200)
    assert set(seen) <= {"1.4", "1.5"}, f"Có request lỗi: {seen}"
    assert 5 <= seen.get("1.5", 0) <= 45, f"Mong đợi khoảng 10% tới api-canary (20 trên 200), thấy {seen}"
    assert seen.get("1.4", 0) >= 155, seen


def test_header_forces_canary(routed):
    lab, _ = routed
    assert call(lab, lab.hostname, "/healthz", 20, "always") == {"1.5": 20}, "Header X-Canary: always phải luôn tới api-canary"
