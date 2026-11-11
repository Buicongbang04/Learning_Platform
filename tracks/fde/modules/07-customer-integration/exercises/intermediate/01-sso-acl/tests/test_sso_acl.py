"""Hiện trường SSO + ACL. Chạy thẳng tệp này từ gốc repo (`PYTHONPATH=. uv run python <tệp> [--apply-idp]`) để dựng
đúng cảnh của test và tự điều tra: VM, Keycloak, quillo với cấu hình trong starter/ (hoặc solutions/ khi SOLUTION=1)."""

import io
import json
import re
import secrets
import shlex
import subprocess
import tarfile
import time
from pathlib import Path

import pytest
import requests

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
SNAPSHOT = "07-customer-integration-quillo"
QUILLO = "/home/fde/quillo-1.0.0"
MEMORY_MB = 3072
ALLOWED_KEYS = {"QUILLO_OIDC_ISSUER", "QUILLO_OIDC_CLIENT_ID", "QUILLO_OIDC_GROUPS_CLAIM", "QUILLO_ACL",
                "QUILLO_OIDC_CA_FILE"}
CHANGE_TYPES = {"add-protocol-mapper", "add-default-client-scope", "set-redirect-uris"}
ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")
FOLDERS = {
    "legal": ["Pháp chế/Hợp đồng/NDA Minh Phát.txt", "Pháp chế/Hợp đồng/Dịch vụ tư vấn Hoà Bình.txt",
              "Pháp chế/Quy chế bảo mật.txt"],
    "finance": ["Tài chính/Hoá đơn quý 3.txt", "Tài chính/Ngân sách 2025.txt"],
    "board": ["Ban giám đốc/Biên bản họp HĐQT.txt"],
}
TOPICS = {
    "legal": "Điều khoản bảo mật: bên nhận thông tin không tiết lộ cho bên thứ ba trong {n} năm, phạt vi phạm {m} triệu.",
    "finance": "Tổng chi phí quý là {m} triệu đồng, thanh toán trong {n} ngày kể từ ngày nhận hoá đơn.",
    "board": "Hội đồng quản trị quyết định tăng vốn điều lệ thêm {m} tỷ đồng trong {n} tháng tới.",
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


def parse_env(path: Path) -> list[str]:
    lines = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ENV_LINE.match(line)
        if not match:
            pytest.fail(f"{path.name}:{n}: cần dạng KHOÁ=giá_trị, có {raw!r}")
        if match.group(1) not in ALLOWED_KEYS:
            pytest.fail(f"{path.name}:{n}: chỉ được đặt {sorted(ALLOWED_KEYS)}, có {match.group(1)}")
        lines.append(line)
    return lines


def parse_request(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        pytest.fail(f"{path.name} không phải JSON hợp lệ: {error}")
    if not isinstance(data, dict) or data.get("client") != "quillo" or not isinstance(data.get("changes"), list):
        pytest.fail(f"{path.name}: cần object có \"client\": \"quillo\" và mảng \"changes\"")
    changes = data["changes"]
    if len(changes) > 5:
        pytest.fail(f"{path.name}: tối đa 5 thay đổi, có {len(changes)}")
    for i, change in enumerate(changes):
        where = f"{path.name}: changes[{i}]"
        if not isinstance(change, dict) or change.get("type") not in CHANGE_TYPES:
            pytest.fail(f"{where}: \"type\" phải thuộc {sorted(CHANGE_TYPES)}")
        if not str(change.get("why", "")).strip():
            pytest.fail(f"{where}: thiếu \"why\" (IT không áp thay đổi không có lý do)")
        if change["type"] == "add-protocol-mapper":
            mapper = change.get("mapper")
            if not isinstance(mapper, dict) or mapper.get("protocol") != "openid-connect" \
                    or not isinstance(mapper.get("protocolMapper"), str) or not isinstance(mapper.get("name"), str) \
                    or not all(isinstance(v, str) for v in (mapper.get("config") or {}).values()):
                pytest.fail(f"{where}: \"mapper\" phải là ProtocolMapperRepresentation openid-connect "
                            "(name, protocol, protocolMapper, config chỉ gồm chuỗi)")
        elif change["type"] == "add-default-client-scope" and not isinstance(change.get("scope"), str):
            pytest.fail(f"{where}: cần \"scope\" là tên client scope")
        elif change["type"] == "set-redirect-uris" and not (
                isinstance(change.get("uris"), list) and all(isinstance(u, str) for u in change["uris"])):
            pytest.fail(f"{where}: cần \"uris\" là mảng chuỗi")
    return changes


class Scene:
    def __init__(self, site: fdekit.Site, work: Path) -> None:
        self.site = site
        self.vm = site.vm
        self.work = work
        self.api = f"http://127.0.0.1:{site.vm.port(18080)}"
        self.docs: dict[str, set[str]] = {}
        self.admin = ""

    def wait_health(self, label: str, timeout: float = 150) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            try:
                response = requests.get(f"{self.api}/healthz", timeout=5)
                if response.status_code == 200:
                    return
                last = f"HTTP {response.status_code} {response.text[:200]}"
            except requests.RequestException as error:
                last = type(error).__name__
            time.sleep(2)
        logs = sh(self.vm, f"cd {QUILLO} && docker compose ps -a; docker compose logs --tail 25 api", timeout=60)
        pytest.fail(f"{label}: quillo không trả /healthz 200 sau {timeout:.0f} s ({last})\n{logs.stdout[-3000:]}")

    def seed(self) -> None:
        token = sh(self.vm, f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {QUILLO}/.env").stdout.strip()
        assert len(token) >= 16, "Không đọc được QUILLO_ADMIN_TOKEN trong .env của snapshot"
        self.admin = token
        buffer = io.BytesIO()
        old = time.time() - 86400
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for group, paths in FOLDERS.items():
                for path in paths:
                    text = (f"{Path(path).stem}. Mã tài liệu {secrets.token_hex(3).upper()}. "
                            + TOPICS[group].format(n=2 + secrets.randbelow(5), m=100 + secrets.randbelow(900)))
                    data = text.encode()
                    info = tarfile.TarInfo(path)
                    info.size, info.mtime, info.mode = len(data), old, 0o644
                    tar.addfile(info, io.BytesIO(data))
        seed = self.work / "seed.tar"
        seed.write_bytes(buffer.getvalue())
        self.vm.put(seed, "/home/fde/seed.tar")
        done = sh(self.vm, f"cd {QUILLO} && sudo -n rm -rf .seed && sudo -n mkdir .seed "
                           "&& sudo -n tar -x -C .seed -f /home/fde/seed.tar && sudo -n chown -R 10001:10001 .seed "
                           "&& sudo -n sh -c 'mv .seed/* inbox/' && sudo -n rmdir .seed && rm /home/fde/seed.tar")
        assert done.returncode == 0, f"Test không đặt được tài liệu vào inbox: {done.stderr}"
        wanted = {path for paths in FOLDERS.values() for path in paths}
        deadline = time.monotonic() + 120
        stored: list[dict] = []
        while time.monotonic() < deadline:
            stored = self.documents(self.admin)
            if len(stored) >= len(wanted):
                break
            time.sleep(2)
        if len(stored) < len(wanted):
            pytest.fail(f"Worker chưa nạp đủ {len(wanted)} tài liệu sau 120 s: {stored}")
        by_name = {d["filename"]: d["doc_id"] for d in stored}
        for group, paths in FOLDERS.items():
            self.docs[group] = set()
            for path in paths:
                match = [doc for name, doc in by_name.items() if name.rsplit("/", 1)[-1] == clean(Path(path).name)]
                assert match, f"Không thấy tài liệu {path} trong {sorted(by_name)}"
                self.docs[group].add(match[0])

    def documents(self, token: str) -> list[dict]:
        response = requests.get(f"{self.api}/api/documents", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if response.status_code != 200:
            pytest.fail(f"GET /api/documents trả {response.status_code}: {response.text[:300]}")
        return response.json()

    def configure(self, env_lines: list[str]) -> None:
        keys = sorted({line.split("=", 1)[0] for line in env_lines} | {"QUILLO_OIDC_ISSUER", "QUILLO_OIDC_CLIENT_ID",
                                                                         "QUILLO_ACL", "QUILLO_OIDC_GROUPS_CLAIM"})
        (self.work / "sso.env").write_text("\n".join(env_lines) + "\n")
        (self.work / "client-secret").write_text(self.site.keycloak_client[1])
        self.vm.put(self.work / "sso.env", "/home/fde/sso.env")
        self.vm.put(self.work / "client-secret", "/home/fde/handover-client-secret")
        drop = " ".join(f"-e '/^{key}=/d'" for key in keys)
        script = (f"set -e; cd {QUILLO}; sed -i {drop} .env; cat /home/fde/sso.env >> .env; "
                  "sudo -n install -d -o 10001 -g 10001 -m 0700 oidc; "
                  "sudo -n install -o 10001 -g 10001 -m 0400 /home/fde/handover-client-secret oidc/client-secret; "
                  "rm -f /home/fde/handover-client-secret /home/fde/sso.env; "
                  "docker compose -f compose.yaml -f compose.sso.yaml up -d 2>&1")
        done = sh(self.vm, script, timeout=180)
        if done.returncode != 0:
            pytest.fail(f"docker compose với cấu hình SSO của bạn lỗi:\n{done.stdout[-2500:]}{done.stderr[-1500:]}")
        self.wait_health("Sau khi áp sso.env", timeout=120)

    def keycloak_admin(self) -> tuple[str, dict]:
        response = requests.post(
            f"{self.site.keycloak_host}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli", "username": self.site.keycloak_admin[0],
                  "password": self.site.keycloak_admin[1]}, timeout=30)
        response.raise_for_status()
        return (f"{self.site.keycloak_host}/admin/realms/{fdekit.KEYCLOAK_REALM}",
                {"Authorization": f"Bearer {response.json()['access_token']}"})

    def apply_request(self, changes: list[dict]) -> None:
        base, auth = self.keycloak_admin()
        [client] = requests.get(f"{base}/clients", params={"clientId": "quillo"}, headers=auth, timeout=30).json()
        url = f"{base}/clients/{client['id']}"
        for i, change in enumerate(changes):
            if change["type"] == "add-protocol-mapper":
                done = requests.post(f"{url}/protocol-mappers/models", headers=auth, json=change["mapper"], timeout=30)
            elif change["type"] == "add-default-client-scope":
                scopes = requests.get(f"{base}/client-scopes", headers=auth, timeout=30).json()
                found = [s for s in scopes if s.get("name") == change["scope"]]
                if not found:
                    pytest.fail(f"IT không áp được changes[{i}]: realm không có client scope {change['scope']!r}")
                done = requests.put(f"{url}/default-client-scopes/{found[0]['id']}", headers=auth, timeout=30)
            else:
                current = requests.get(url, headers=auth, timeout=30).json()
                done = requests.put(url, headers=auth, json=current | {"redirectUris": change["uris"]}, timeout=30)
            if done.status_code not in (200, 201, 204):
                pytest.fail(f"IT không áp được changes[{i}] ({change['type']}): Keycloak trả {done.status_code} "
                            f"{done.text[:300]}")

    def token(self, user: str) -> str:
        return fdekit.keycloak_token(self.site, user, fdekit.KEYCLOAK_PASSWORDS[user])


def clean(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name)


def submission() -> tuple[list[str], list[dict]]:
    return parse_env(ex.path("sso.env")), parse_request(ex.path("idp-request.json"))


def visible(scene: Scene, user: str) -> set[str]:
    token = scene.token(user)
    me = requests.get(f"{scene.api}/api/me", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    assert me.status_code == 200, f"Token SSO của {user} bị quillo từ chối (/api/me trả {me.status_code}): {me.text[:300]}"
    return {d["doc_id"] for d in scene.documents(token)}


def cited(scene: Scene, user: str, question: str) -> set[str]:
    response = requests.post(f"{scene.api}/api/ask", headers={"Authorization": f"Bearer {scene.token(user)}"},
                             json={"question": question, "top_k": 4}, timeout=120)
    assert response.status_code == 200, f"/api/ask của {user} trả {response.status_code}: {response.text[:300]}"
    return {c["doc_id"] for c in response.json().get("citations", [])}


def test_sso_users_see_their_folders(tmp_path):
    env_lines, changes = submission()
    base = fdekit.derived(SNAPSHOT)
    with fdekit.customer_site("lab-open", base=base, memory_mb=MEMORY_MB, forwards=(18080,),
                              extra_services=("keycloak",)) as site:
        scene = Scene(site, tmp_path)
        scene.wait_health("Sau khi boot snapshot")
        scene.seed()
        scene.configure(env_lines)
        scene.apply_request(changes)

        legal, finance, board = scene.docs["legal"], scene.docs["finance"], scene.docs["board"]
        everything = legal | finance | board
        assert {d["doc_id"] for d in scene.documents(scene.admin)} == everything, \
            "Token quản trị phải còn thấy mọi tài liệu"
        seen = {user: visible(scene, user) for user in ("an", "binh", "chi")}
        assert seen["an"] == legal, (f"an (nhóm legal) thấy {len(seen['an'])} tài liệu, cần đúng {len(legal)} tài liệu "
                                     f"của Pháp chế (thừa {len(seen['an'] - legal)}, thiếu {len(legal - seen['an'])})")
        assert seen["binh"] == finance, (f"binh (nhóm finance) thấy {len(seen['binh'])} tài liệu, cần đúng {len(finance)} "
                                         f"của Tài chính (thừa {len(seen['binh'] - finance)}, "
                                         f"thiếu {len(finance - seen['binh'])})")
        assert seen["chi"] == legal | finance, "chi (legal + finance) phải thấy đúng Pháp chế và Tài chính"
        an_cites = cited(scene, "an", "Điều khoản bảo mật phạt vi phạm bao nhiêu?")
        assert an_cites and an_cites <= legal, f"/api/ask của an phải trích dẫn chỉ tài liệu Pháp chế, có {an_cites}"
        binh_cites = cited(scene, "binh", "Điều khoản bảo mật phạt vi phạm bao nhiêu?")
        assert binh_cites <= finance, "/api/ask của binh trích dẫn tài liệu ngoài Tài chính"


def main() -> None:
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Dựng cảnh của bài để điều tra")
    parser.add_argument("--apply-idp", action="store_true", help="áp luôn idp-request.json như IT")
    parser.add_argument("--no-sso", action="store_true", help="không áp sso.env (quillo như trong snapshot)")
    args = parser.parse_args()
    env_lines, changes = submission()
    with tempfile.TemporaryDirectory() as work, fdekit.customer_site(
            "lab-open", base=fdekit.derived(SNAPSHOT), memory_mb=MEMORY_MB, forwards=(18080,),
            extra_services=("keycloak",)) as site:
        scene = Scene(site, Path(work))
        scene.wait_health("Sau khi boot snapshot")
        scene.seed()
        if not args.no_sso:
            scene.configure(env_lines)
        if args.apply_idp:
            scene.apply_request(changes)
        users = ", ".join(f"{u}/{p}" for u, p in fdekit.KEYCLOAK_PASSWORDS.items())
        print(f"""
SSH vào máy khách:   {shlex.join(site.vm.ssh_command())}
quillo (từ host):    {scene.api}   (cài ở {QUILLO}, token quản trị trong .env)
Keycloak (từ host):  {site.keycloak_host}   realm {fdekit.KEYCLOAK_REALM}, client quillo
  client secret:     {site.keycloak_client[1]}
  user:              {users}
  admin (chỉ lab):   {site.keycloak_admin[0]} / {site.keycloak_admin[1]}  (admin REST API: {site.keycloak_host}/admin/realms/...)
Nhấn Enter để dọn máy.""")
        input()


if __name__ == "__main__":
    main()
