import json
import random
import shlex
import subprocess
import time

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
WORK = "/home/fde/can-i"
KUBECONFIG = "/home/fde/.kube/config"
RUN_TIMEOUT = 90
K8S_WAIT = 180
SECRETS_GONE = ["pods", "pods/log", "pods/exec", "pods/portforward", "pods/attach", "services", "configmaps",
                "persistentvolumeclaims", "serviceaccounts"]
NODE_READER = """apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata: {name: fde-node-reader}
rules:
  - apiGroups: [""]
    resources: [nodes]
    verbs: [get, list]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata: {name: fde-node-reader}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: fde-node-reader}
subjects:
  - {kind: ServiceAccount, name: fde, namespace: quillo}
"""


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def wait_api(m) -> None:
    deadline = time.monotonic() + K8S_WAIT
    while time.monotonic() < deadline:
        if sh(m, "kubectl --request-timeout=5s get --raw=/readyz", timeout=30).stdout.strip() == "ok":
            return
        time.sleep(2)
    pytest.fail(f"API server k3s chưa sẵn sàng sau {K8S_WAIT} s")


def read_checks() -> list[tuple[str, str]]:
    rows = []
    for line in (ex.dir / "checks.txt").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            kind, args = line.split(None, 1)
            rows.append((kind, " ".join(args.split())))
    return rows


def checks_file(rows: list[tuple[str, str]], rng: random.Random) -> tuple[str, list[tuple[str, str]]]:
    picked = rng.sample(rows, len(rows) - 3)
    lines = ["# danh sách quyền cho lần chạy này", ""]
    for kind, args in picked:
        lines.append(f"{kind}   {args}" if rng.random() < 0.3 else f"{kind} {args}")
        if rng.random() < 0.2:
            lines.append("")
    return "\n".join(lines) + "\n", picked


def truth(m, rows: list[tuple[str, str]], env: str) -> dict:
    checks = {}
    for _, args in rows:
        out = sh(m, f"{env} kubectl auth can-i {args} 2>/dev/null").stdout.strip()
        assert out in ("yes", "no"), f"Test không hỏi được quyền '{args}' (kubectl in {out!r})"
        checks[args] = out == "yes"
    missing = [args for kind, args in rows if kind == "need" and not checks[args]]
    return {"checks": checks, "missing": missing, "can_install": not missing}


def run_script(m, env: str, attempt: str) -> subprocess.CompletedProcess:
    return sh(m, f"cd /tmp && {env} sh {WORK}/can_i.sh {WORK}/checks.txt 2>{WORK}/stderr.txt", timeout=RUN_TIMEOUT)


def check_report(m, env: str, rows, user: str, namespace: str, attempt: str) -> None:
    expected = truth(m, rows, env)
    run = run_script(m, env, attempt)
    err = sh(m, f"tail -c 1500 {WORK}/stderr.txt").stdout
    assert run.returncode == 0, f"{attempt}: can_i.sh thoát mã {run.returncode}\nstdout:\n{run.stdout[-1500:]}\nstderr:\n{err}"
    try:
        report = json.loads(run.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"{attempt}: stdout của can_i.sh phải là đúng một object JSON, nhận:\n{run.stdout[:1500]}")
    assert isinstance(report, dict), f"{attempt}: stdout phải là object JSON"
    assert report.get("user") == user, f"{attempt}: user phải là {user!r}, nhận {report.get('user')!r}"
    assert report.get("namespace") == namespace, (
        f"{attempt}: namespace phải là {namespace!r}, nhận {report.get('namespace')!r}")
    got = report.get("checks")
    assert isinstance(got, dict) and set(got) == set(expected["checks"]), (
        f"{attempt}: checks phải có đúng một khoá cho mỗi dòng của tệp kiểm tra.\n"
        f"thiếu: {sorted(set(expected['checks']) - set(got or {}))}\nthừa: {sorted(set(got or {}) - set(expected['checks']))}")
    wrong = {k: v for k, v in got.items() if v is not expected["checks"][k]}
    assert not wrong, f"{attempt}: checks khác `kubectl auth can-i` thật ở: {wrong}"
    assert report.get("missing") == expected["missing"], (
        f"{attempt}: missing phải là {expected['missing']}, nhận {report.get('missing')}")
    assert report.get("can_install") is expected["can_install"], (
        f"{attempt}: can_install phải là {expected['can_install']}, nhận {report.get('can_install')!r}")


def test_can_i_on_lawfirm_prod():
    rng = random.Random()
    rows = read_checks()
    user = "system:serviceaccount:quillo:fde"
    with fdekit.vm("lawfirm-prod", sudo=True) as m:
        wait_api(m)
        assert sh(m, f"mkdir -p {WORK}").returncode == 0
        m.put(ex.path("can_i.sh"), f"{WORK}/can_i.sh")

        text, picked = checks_file(rows, rng)
        assert sh(m, f"printf %s {shlex.quote(text)} > {WORK}/checks.txt").returncode == 0
        check_report(m, "", picked, user, "quillo", "lần 1 (kubeconfig của fde)")

        other = "/home/fde/.kube/other-ns"
        done = sh(m, f"cp {KUBECONFIG} {other} && KUBECONFIG={other} kubectl config set-context --current "
                     f"--namespace=default >/dev/null")
        assert done.returncode == 0, done.stderr
        text, picked = checks_file(rows, rng)
        assert sh(m, f"printf %s {shlex.quote(text)} > {WORK}/checks.txt").returncode == 0
        check_report(m, f"KUBECONFIG={other}", picked, user, "default", "lần 2 (context trỏ namespace default)")

        broken = "/home/fde/.kube/broken"
        port = rng.randint(20000, 30000)
        done = sh(m, f"cp {KUBECONFIG} {broken} && sed -i 's#https://127.0.0.1:6443#https://127.0.0.1:{port}#' {broken}")
        assert done.returncode == 0, done.stderr
        run = run_script(m, f"KUBECONFIG={broken}", "lần 3")
        assert run.returncode != 0, "lần 3 (API server không với tới được): can_i.sh phải thoát mã khác 0"
        assert run.stdout.strip() == "", (
            f"lần 3 (API server không với tới được): stdout phải rỗng, không được in báo cáo:\n{run.stdout[:800]}")

        role = json.loads(sh(m, "sudo -n k3s kubectl -n quillo get role fde-deployer -o json").stdout)
        role["rules"][0]["resources"] = SECRETS_GONE
        role.pop("status", None)
        done = sh(m, f"printf %s {shlex.quote(json.dumps(role))} | sudo -n k3s kubectl apply -f - && "
                     f"printf %s {shlex.quote(NODE_READER)} | sudo -n k3s kubectl apply -f -")
        assert done.returncode == 0, f"Test không đổi được RBAC: {done.stderr}"
        text, picked = checks_file(rows, rng)
        if not any(args == "create secrets" for _, args in picked):
            picked.append(("need", "create secrets"))
            text += "need create secrets\n"
        assert sh(m, f"printf %s {shlex.quote(text)} > {WORK}/checks.txt").returncode == 0
        check_report(m, "", picked, user, "quillo", "lần 4 (IT đã đổi Role: bỏ secrets, thêm quyền đọc nodes)")
