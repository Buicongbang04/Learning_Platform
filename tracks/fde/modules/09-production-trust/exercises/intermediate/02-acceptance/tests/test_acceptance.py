"""Acceptance test của quillo, chấm trên quillo thật trong VM ở ba trạng thái. Chạy thẳng tệp này từ gốc repo
(`PYTHONPATH=. uv run python <tệp>`) để dựng quillo đã bật SSO + ACL, in cấu hình mẫu và chờ Enter."""

import json
import secrets
import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

import fdekit
from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
SNAPSHOT = "07-customer-integration-quillo"
QUILLO = "/home/fde/quillo-1.0.0"
MEMORY_MB = 3072
TOP_K = 2
SAMPLES = 4
RUN_TIMEOUT = 150
MIN_P95 = 0.05
ACL = "legal:legal/,finance:finance/"
WRONG_ACL = "legal:legal/,legal:finance/,finance:finance/"
LATENCY_QUESTIONS = [
    "How many days of written notice does the consultant need to terminate?",
    "How long must the receiving party keep information confidential?",
    "What is the total operating cost in the budget 2027?",
    "How many invoices were paid late in quarter three?",
]
GROUPS_MAPPER = {"name": "groups", "protocol": "openid-connect", "protocolMapper": "oidc-group-membership-mapper",
                 "config": {"claim.name": "groups", "full.path": "false", "access.token.claim": "true",
                            "id.token.claim": "true", "userinfo.token.claim": "true"}}
DOCS = {
    "legal": [("legal/nda-minh-phat.txt", "Non-disclosure agreement with Minh Phat: the receiving party keeps "
               "information confidential for {n} years and pays a penalty of {m} million VND for each breach."),
              ("legal/consulting-hoa-binh.txt", "Consulting services agreement with Hoa Binh: the consultant may "
               "terminate with {n} days written notice; the fee is {m} million VND per month.")],
    "finance": [("finance/budget-2027.txt", "Budget 2027 of the finance department: total operating cost is {m} "
                 "million VND, invoices are paid within {n} days of receipt."),
                ("finance/invoice-q3.txt", "Invoice summary for quarter three: {m} invoices were paid late by an "
                 "average of {n} days.")],
}


def sh(m: fdekit.VM, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    for attempt in range(3):
        try:
            done = m.ssh(cmd, timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")
        if done.returncode != 255 or attempt == 2:
            return done
        time.sleep(2)
    return done


class Scene:
    def __init__(self, site: fdekit.Site, work: Path) -> None:
        self.site = site
        self.vm = site.vm
        self.work = work
        self.api = f"http://127.0.0.1:{site.vm.port(18080)}"
        self.admin = ""
        self.ids: dict[str, set[str]] = {}

    def wait_health(self, label: str, timeout: float = 150) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            try:
                response = requests.get(f"{self.api}/healthz", timeout=5)
                if response.status_code == 200:
                    return
                last = f"HTTP {response.status_code}"
            except requests.RequestException as error:
                last = type(error).__name__
            time.sleep(2)
        logs = sh(self.vm, f"cd {QUILLO} && docker compose ps -a; docker compose logs --tail 20 api", timeout=60)
        pytest.fail(f"{label}: quillo không trả /healthz 200 sau {timeout:.0f} s ({last})\n{logs.stdout[-2500:]}")

    def seed(self) -> None:
        self.admin = sh(self.vm, f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {QUILLO}/.env").stdout.strip()
        assert len(self.admin) >= 16, "Không đọc được QUILLO_ADMIN_TOKEN trong .env của snapshot"
        for group, docs in DOCS.items():
            self.ids[group] = set()
            for path, template in docs:
                folder, name = path.split("/")
                text = template.format(n=2 + secrets.randbelow(20), m=100 + secrets.randbelow(900))
                response = requests.post(f"{self.api}/api/documents", headers={"Authorization": f"Bearer {self.admin}"},
                                         data={"folder": folder}, files={"file": (name, text.encode(), "text/plain")},
                                         timeout=120)
                assert response.status_code == 201, f"Nạp {path} trả {response.status_code}: {response.text[:300]}"
                self.ids[group].add(response.json()["doc_id"])

    def configure(self, acl: str) -> None:
        (self.work / "client-secret").write_text(self.site.keycloak_client[1])
        self.vm.put(self.work / "client-secret", "/home/fde/handover-client-secret")
        lines = [f"QUILLO_OIDC_ISSUER={self.site.keycloak}/realms/{fdekit.KEYCLOAK_REALM}", "QUILLO_OIDC_CLIENT_ID=quillo",
                 "QUILLO_OIDC_GROUPS_CLAIM=groups", f"QUILLO_ACL={acl}"]
        drop = " ".join(f"-e '/^{line.split('=')[0]}=/d'" for line in lines)
        add = "; ".join(f"echo {shlex.quote(line)} >> .env" for line in lines)
        script = (f"set -e; cd {QUILLO}; sed -i {drop} .env; {add}; "
                  "sudo -n install -d -o 10001 -g 10001 -m 0700 oidc; "
                  "sudo -n install -o 10001 -g 10001 -m 0400 /home/fde/handover-client-secret oidc/client-secret; "
                  "rm -f /home/fde/handover-client-secret; docker compose -f compose.yaml -f compose.sso.yaml up -d 2>&1")
        done = sh(self.vm, script, timeout=180)
        assert done.returncode == 0, f"Test không bật được SSO cho quillo: {done.stdout[-2000:]}"
        self.wait_health(f"Sau khi đặt QUILLO_ACL={acl}", timeout=120)

    def add_groups_mapper(self) -> None:
        token = requests.post(f"{self.site.keycloak_host}/realms/master/protocol/openid-connect/token",
                              data={"grant_type": "password", "client_id": "admin-cli",
                                    "username": self.site.keycloak_admin[0], "password": self.site.keycloak_admin[1]},
                              timeout=30)
        token.raise_for_status()
        auth = {"Authorization": f"Bearer {token.json()['access_token']}"}
        base = f"{self.site.keycloak_host}/admin/realms/{fdekit.KEYCLOAK_REALM}"
        [client] = requests.get(f"{base}/clients", params={"clientId": "quillo"}, headers=auth, timeout=30).json()
        done = requests.post(f"{base}/clients/{client['id']}/protocol-mappers/models", headers=auth,
                             json=GROUPS_MAPPER, timeout=30)
        assert done.status_code in (200, 201), f"Test không thêm được mapper groups: {done.status_code} {done.text}"

    def token(self, user: str) -> str:
        return fdekit.keycloak_token(self.site, user, fdekit.KEYCLOAK_PASSWORDS[user])

    def baseline_p95(self, questions: list[str]) -> float:
        durations = []
        for question in questions[:3]:
            started = time.monotonic()
            response = requests.post(f"{self.api}/api/ask", headers={"Authorization": f"Bearer {self.admin}"},
                                     json={"question": question, "top_k": TOP_K}, timeout=120)
            assert response.status_code == 200, f"/api/ask lúc đo mốc trả {response.status_code}"
            durations.append(time.monotonic() - started)
        return max(durations)

    def config(self, threshold: float) -> dict:
        return {
            "url": self.api,
            "admin_token": self.admin,
            "top_k": TOP_K,
            "latency_samples": SAMPLES,
            "latency_questions": LATENCY_QUESTIONS,
            "p95_max_seconds": threshold,
            "questions": [
                {"question": "What penalty applies for each breach of the non-disclosure agreement?",
                 "expect_folder": "legal/"},
                {"question": "Within how many days are invoices paid according to the budget 2027?",
                 "expect_folder": "finance/"},
            ],
            "users": [
                {"name": "an", "token": self.token("an"), "folders": ["legal/"],
                 "probe": "What is the total operating cost in the budget 2027?"},
                {"name": "binh", "token": self.token("binh"), "folders": ["finance/"],
                 "probe": "What penalty applies for each breach of the non-disclosure agreement?"},
            ],
        }

    def run(self, cfg: dict, label: str) -> tuple[int, dict]:
        run_dir = self.work / label
        run_dir.mkdir()
        (run_dir / "acceptance.json").write_text(json.dumps(cfg))
        try:
            done = run_sandboxed([sys.executable, str(ex.path("acceptance.py")), "--config", "acceptance.json",
                                  "--out", "report.json"], writable=[run_dir], cwd=run_dir, env={},
                                 timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.fail(f"{label}: acceptance.py chạy quá {RUN_TIMEOUT} s")
        report_path = run_dir / "report.json"
        assert report_path.is_file(), (f"{label}: acceptance.py (thoát {done.returncode}) không ghi report.json\n"
                                       f"{done.stdout[-1500:]}{done.stderr[-1500:]}")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            pytest.fail(f"{label}: report.json không phải JSON: {error}")
        assert isinstance(report.get("items"), list), f"{label}: report.json thiếu mảng items"
        return done.returncode, report


def statuses(report: dict, label: str) -> dict[str, str]:
    out = {}
    for row in report["items"]:
        assert isinstance(row, dict) and row.get("id") in ("health", "latency", "citations", "acl"), \
            f"{label}: mục lạ trong items: {row!r}"
        assert row.get("status") in ("PASS", "FAIL"), f"{label}: status của {row.get('id')} phải là PASS hoặc FAIL"
        assert isinstance(row.get("detail"), str), f"{label}: thiếu detail cho {row.get('id')}"
        out[row["id"]] = row["status"]
    assert set(out) == {"health", "latency", "citations", "acl"}, f"{label}: cần đủ 4 mục, có {sorted(out)}"
    return out


def expect(code: int, report: dict, label: str, want: dict[str, str]) -> None:
    got = statuses(report, label)
    assert got == want, f"{label}: cần {want}, acceptance.py báo {got}"
    passed = all(v == "PASS" for v in want.values())
    assert report.get("passed") is passed, f"{label}: passed phải là {passed}"
    assert code == (0 if passed else 1), f"{label}: mã thoát phải là {0 if passed else 1}, có {code}"


def test_acceptance_against_real_quillo(tmp_path):
    with fdekit.customer_site("lab-open", base=fdekit.derived(SNAPSHOT), memory_mb=MEMORY_MB, forwards=(18080,),
                              extra_services=("keycloak",)) as site:
        scene = Scene(site, tmp_path)
        scene.wait_health("Sau khi boot snapshot")
        scene.seed()
        scene.add_groups_mapper()
        scene.configure(ACL)
        cfg = scene.config(1.0)
        base = scene.baseline_p95(cfg["latency_questions"])
        threshold = round(max(2 * base, 1.0), 2)

        code, report = scene.run(scene.config(threshold), "healthy")
        expect(code, report, "quillo khoẻ", {"health": "PASS", "latency": "PASS", "citations": "PASS", "acl": "PASS"})
        p95 = report.get("p95_seconds")
        assert isinstance(p95, (int, float)) and MIN_P95 <= p95 <= threshold, \
            f"p95_seconds {p95!r} phải là số giây đo thật, từ {MIN_P95} tới ngưỡng {threshold} s"

        scene.configure(WRONG_ACL)
        code, report = scene.run(scene.config(0.001), "acl-and-slow")
        expect(code, report, "ACL cấu hình sai + ngưỡng p95 0,001 s",
               {"health": "PASS", "latency": "FAIL", "citations": "PASS", "acl": "FAIL"})

        stopped = sh(scene.vm, f"cd {QUILLO} && docker compose -f compose.yaml -f compose.sso.yaml stop embed",
                     timeout=60)
        assert stopped.returncode == 0, f"Test không dừng được embed: {stopped.stderr}"
        code, report = scene.run(scene.config(threshold), "embed-down")
        expect(code, report, "embed bị dừng", {"health": "FAIL", "latency": "FAIL", "citations": "FAIL", "acl": "FAIL"})
        health = next(r for r in report["items"] if r["id"] == "health")
        assert "embed" in health["detail"], f"detail của health phải nêu thành phần hỏng (embed): {health['detail']!r}"


def main() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as work, fdekit.customer_site(
            "lab-open", base=fdekit.derived(SNAPSHOT), memory_mb=MEMORY_MB, forwards=(18080,),
            extra_services=("keycloak",)) as site:
        scene = Scene(site, Path(work))
        scene.wait_health("Sau khi boot snapshot")
        scene.seed()
        scene.add_groups_mapper()
        scene.configure(ACL)
        path = Path(work) / "acceptance.json"
        path.write_text(json.dumps(scene.config(10.0), indent=2))
        print(f"""
SSH vào máy:     {shlex.join(site.vm.ssh_command())}
quillo:          {scene.api}   (cài ở {QUILLO})
Cấu hình mẫu:    {path}   (token SSO hết hạn sau vài phút: chạy lại tệp này để lấy mới)
Chạy:            python acceptance.py --config {path} --out report.json
Nhấn Enter để dọn máy.""")
        input()


if __name__ == "__main__":
    sys.exit(main())
