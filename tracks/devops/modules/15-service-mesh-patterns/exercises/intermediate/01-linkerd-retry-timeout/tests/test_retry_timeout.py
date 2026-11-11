import json
import re
import subprocess
import time

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
BACKEND = ex.fixtures / "freight.yaml"
SCRIPT = ex.fixtures / "freight_quote.py"
GROUP = "httproutes.policy.linkerd.io"
LOAD = """
import json, sys, time, urllib.error, urllib.request
count, method, path = int(sys.argv[1]), sys.argv[2], sys.argv[3]
codes, latencies = {}, []
for _ in range(count):
    request = urllib.request.Request("http://freight:8080" + path, method=method, data=b"{}" if method == "POST" else None)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=6) as answer:
            answer.read()
            code = str(answer.status)
    except urllib.error.HTTPError as error:
        code = str(error.code)
    except Exception as error:
        code = type(error).__name__
    latencies.append(time.monotonic() - start)
    codes[code] = codes.get(code, 0) + 1
print(json.dumps({"count": count, "codes": codes, "max": max(latencies), "p50": sorted(latencies)[count // 2]}))
"""
STATS = "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/stats', timeout=5).read().decode())"
DURATION = re.compile(r"^(\d+(?:\.\d+)?)(ms|s|m)$")


def load(lab, count: int, method: str, path: str) -> dict:
    result = lab.kubectl("exec", "deployment/checkout", "-c", "checkout", "--", "python", "-c", LOAD, str(count), method, path,
                         check=False, timeout=count * 7 + 60)
    assert result.returncode == 0, f"Không chạy được tải từ checkout: {result.stderr[-400:]}"
    return json.loads(result.stdout)


def backend_counts(lab) -> dict:
    result = lab.kubectl("exec", "deployment/freight", "-c", "freight", "--", "python", "-c", STATS, check=False, timeout=60)
    assert result.returncode == 0, f"Không đọc được /stats của freight: {result.stderr[-400:]}"
    return json.loads(result.stdout)


def seconds(value) -> float | None:
    match = DURATION.match(str(value or "").strip())
    if not match:
        return None
    return float(match.group(1)) * {"ms": 0.001, "s": 1, "m": 60}[match.group(2)]


def routes(lab) -> list[dict]:
    return json.loads(lab.kubectl("get", GROUP, "-o", "json").stdout).get("items") or []


def accepted(route: dict) -> bool:
    parents = (route.get("status") or {}).get("parents") or []
    return bool(parents) and all(any(c.get("type") == "Accepted" and c.get("status") == "True" for c in p.get("conditions") or [])
                                 for p in parents)


def matching(route: dict, method: str, path: str) -> bool:
    for rule in (route.get("spec") or {}).get("rules") or []:
        for match in rule.get("matches") or [{}]:
            want = match.get("method")
            rule_path = match.get("path") or {"type": "PathPrefix", "value": "/"}
            value = rule_path.get("value", "/")
            hit = path == value if rule_path.get("type") == "Exact" else path.startswith(value.rstrip("/") + "/") or \
                path == value or value == "/"
            if hit and want in (None, method):
                return True
    return False


@pytest.fixture(scope="module")
def traffic():
    ex.require_linkerd()
    ex.require_kind_images(KUBE_IMAGES["olist"])
    with KubeLab(mesh=True) as lab:
        lab.kubectl("create", "configmap", "freight-code", f"--from-file=freight_quote.py={SCRIPT}")
        lab.apply_learner(BACKEND)
        for name in ("freight", "checkout"):
            lab.kubectl("rollout", "status", f"deployment/{name}", "--timeout=180s", timeout=200)
        control = load(lab, 60, "GET", "/quote")
        try:
            applied = lab.apply_learner(ex.path("k8s"), check=False)
        except pytest.fail.Exception as error:
            applied = subprocess.CompletedProcess([], 1, "", str(error))
        deadline = time.monotonic() + 40
        while applied.returncode == 0 and time.monotonic() < deadline:
            current = routes(lab)
            if current and all(accepted(r) for r in current):
                break
            time.sleep(2)
        time.sleep(5)
        before = backend_counts(lab)
        quotes = load(lab, 200, "GET", "/quote")
        middle = backend_counts(lab)
        reserves = load(lab, 40, "POST", "/reserve")
        after = backend_counts(lab)
        yield {"lab": lab, "applied": applied, "control": control, "quotes": quotes, "reserves": reserves,
               "quote_calls": middle["GET /quote"] - before["GET /quote"],
               "reserve_calls": after["POST /reserve"] - middle["POST /reserve"]}


def test_control_backend_is_flaky_and_slow(traffic):
    control = traffic["control"]
    failed = control["count"] - control["codes"].get("200", 0)
    assert failed >= 5 and control["max"] >= 2.0, \
        f"Đối chứng: không có route, freight phải lỗi và chậm thấy rõ (được {control})"


def test_routes_apply_and_accepted(traffic):
    lab, applied = traffic["lab"], traffic["applied"]
    assert applied.returncode == 0, applied.stderr[-1500:]
    current = routes(lab)
    assert current, "Chưa có HTTPRoute policy.linkerd.io nào trong namespace"
    pending = [r["metadata"]["name"] for r in current if not accepted(r)]
    assert not pending, f"HTTPRoute chưa được Linkerd chấp nhận (status Accepted): {pending}"


def test_quote_success_rate(traffic):
    quotes = traffic["quotes"]
    ok = quotes["codes"].get("200", 0)
    assert quotes["count"] == 200 and ok / quotes["count"] >= 0.97, f"GET /quote thành công {ok}/200, cần >= 97%: {quotes}"


def test_quote_latency_bounded(traffic):
    quotes = traffic["quotes"]
    assert quotes["max"] < 2.3, f"Request GET /quote chậm nhất mất {quotes['max']:.2f} s, cần dưới 2,3 s"


def test_retries_are_bounded(traffic):
    calls, sent = traffic["quote_calls"], traffic["quotes"]["count"]
    assert sent > 0 and calls > sent, f"freight nhận {calls} request cho {sent} request GET: chưa có retry nào"
    assert calls <= 1.6 * sent, f"freight nhận {calls} request cho {sent} request GET (> 1,6 lần): retry quá tay"


def test_reserve_not_retried(traffic):
    reserves, calls = traffic["reserves"], traffic["reserve_calls"]
    assert reserves["count"] == 40 and "404" not in reserves["codes"], \
        f"POST /reserve phải tới được freight (404 là không có route nào khớp): {reserves['codes']}"
    assert calls == reserves["count"], f"freight nhận {calls} lần POST /reserve cho {reserves['count']} request: POST bị thử lại"


def test_mesh_counts_retries(traffic):
    status = traffic["lab"].mesh_status("deployment/checkout")
    assert status["injected"] and status["mtls"], f"checkout phải nằm trong mesh: {status}"
    assert status["retries"] > 0, f"Proxy của checkout chưa ghi lần retry nào: {status}"
    assert status["outbound_success"] > 0, status


def test_route_settings(traffic):
    current = routes(traffic["lab"])
    quote = [r for r in current if matching(r, "GET", "/quote")]
    reserve = [r for r in current if matching(r, "POST", "/reserve")]
    assert quote and reserve, "Cần route khớp GET /quote và route khớp POST /reserve"
    for route in quote:
        notes = route["metadata"].get("annotations") or {}
        name = route["metadata"]["name"]
        assert "5xx" in notes.get("retry.linkerd.io/http", ""), f"{name}: retry.linkerd.io/http cần có 5xx"
        limit = notes.get("retry.linkerd.io/limit", "")
        assert limit == "3", f"{name}: retry.linkerd.io/limit phải là 3, đang là {limit!r}"
        per_try = seconds(notes.get("retry.linkerd.io/timeout"))
        assert per_try is not None and per_try <= 0.5, f"{name}: retry.linkerd.io/timeout phải có và không quá 500 ms"
        whole = seconds(notes.get("timeout.linkerd.io/request"))
        assert whole is not None and whole <= 2, f"{name}: timeout.linkerd.io/request phải có và không quá 2 s"
    for route in reserve:
        notes = route["metadata"].get("annotations") or {}
        retrying = [k for k in notes if k.startswith("retry.linkerd.io/")]
        assert not retrying, f"{route['metadata']['name']} khớp POST /reserve nhưng có {retrying}"
