import json
import secrets
import time
import uuid

import pytest

from testkit import VAULT_DEV_TOKEN, Exercise, run_sandboxed, vault_env

ex = Exercise(__file__)
VAULT_CLI_MIN = "1.15"
MAX_TTL = 15 * 60
MAX_EXPLICIT_TTL = 60 * 60


class Vault:
    def __init__(self, tmp_path, token: str, name: str):
        self.tmp = tmp_path
        self.token = token
        self.home = tmp_path / f"home-{name}"

    def run(self, *args: str, input: str | None = None):
        return run_sandboxed(["vault", *args], writable=[self.tmp], cwd=self.tmp, env=vault_env(self.token, self.home),
                             input=input, timeout=30)


def denied(result) -> bool:
    return result.returncode != 0 and "permission denied" in result.stderr.lower()


@pytest.fixture(scope="module")
def vault(tmp_path_factory):
    ex.require_tool("vault", VAULT_CLI_MIN)
    ex.require_vault_devops()
    tmp = tmp_path_factory.mktemp("vault")
    lab = f"devops-ex-{uuid.uuid4().hex[:8]}"
    mount, policy = lab, f"{lab}-olist-api"
    root = Vault(tmp, VAULT_DEV_TOKEN, "root")
    password = secrets.token_urlsafe(18)
    accessors: list[str] = []

    def token(ttl: str | None = None) -> tuple[str, dict]:
        env = {**vault_env(VAULT_DEV_TOKEN, tmp / "home-script"), "POLICY_NAME": policy}
        if ttl:
            env["TOKEN_TTL"] = ttl
        result = run_sandboxed(["bash", str(ex.path("token.sh"))], writable=[tmp], cwd=tmp, env=env, timeout=30)
        value = result.stdout.strip()
        if result.returncode != 0 or not value or "\n" in value:
            return "", {"error": f"token.sh phải in đúng một dòng là token (mã {result.returncode}): {result.stderr.strip()[-500:]}"}
        looked = root.run("token", "lookup", "-format=json", value)
        if looked.returncode != 0:
            return "", {"error": f"Không tra được token do token.sh tạo: {looked.stderr.strip()[-300:]}"}
        data = json.loads(looked.stdout)["data"]
        accessors.append(data["accessor"])
        return value, data

    try:
        setup = [
            root.run("secrets", "enable", f"-path={mount}", "kv-v2"),
            root.run("kv", "put", f"-mount={mount}", "olist/api/db", "username=olist", f"password={password}"),
            root.run("kv", "put", f"-mount={mount}", "olist/api/redis", f"password={secrets.token_urlsafe(12)}"),
            root.run("kv", "put", f"-mount={mount}", "olist/payments/stripe", f"api_key={secrets.token_urlsafe(12)}"),
        ]
        for result in setup:
            assert result.returncode == 0, f"Chuẩn bị Vault lỗi: {result.stderr.strip()[-300:]}"
        rules = ex.read("policy.hcl").replace("KV_MOUNT", mount)
        written = root.run("policy", "write", policy, "-", input=rules)
        yield {"root": root, "tmp": tmp, "mount": mount, "policy": policy, "password": password, "token": token,
               "written": written, "rules": rules}
    finally:
        for accessor in accessors:
            root.run("token", "revoke", "-accessor", accessor)
        root.run("policy", "delete", policy)
        root.run("secrets", "disable", mount)


def test_policy_accepted(vault):
    written = vault["written"]
    assert written.returncode == 0, f"vault policy write từ chối policy.hcl: {written.stderr.strip()[-800:]}"


def test_token_only_carries_lab_policy(vault):
    _, data = vault["token"]()
    assert "error" not in data, data.get("error")
    assert sorted(data["policies"]) == sorted(["default", vault["policy"]]), \
        f"Token chỉ mang policy default và {vault['policy']}, đang có {data['policies']}"
    assert "root" not in data["policies"]


def test_token_ttl_is_short(vault):
    _, data = vault["token"]()
    assert "error" not in data, data.get("error")
    assert 0 < data["creation_ttl"] <= MAX_TTL and 0 < data["ttl"] <= MAX_TTL, \
        f"TTL mặc định của token tối đa {MAX_TTL // 60} phút, đang là {data['creation_ttl']} giây"
    assert 0 < data.get("explicit_max_ttl", 0) <= MAX_EXPLICIT_TTL, \
        f"Đặt explicit max TTL (gia hạn bao nhiêu cũng không quá {MAX_EXPLICIT_TTL // 3600} giờ), đang là {data.get('explicit_max_ttl')}"


def test_token_reads_its_path(vault):
    value, data = vault["token"]()
    assert "error" not in data, data.get("error")
    app = Vault(vault["tmp"], value, "app")
    got = app.run("kv", "get", f"-mount={vault['mount']}", "-field=password", "olist/api/db")
    assert got.returncode == 0, f"Token phải đọc được olist/api/db: {got.stderr.strip()[-300:]}"
    assert got.stdout.strip() == vault["password"], "Giá trị đọc được khác giá trị đã ghi (không in giá trị)"
    listed = app.run("kv", "list", f"-mount={vault['mount']}", "-format=json", "olist/api")
    assert listed.returncode == 0, f"Token phải liệt kê được khoá dưới olist/api (metadata): {listed.stderr.strip()[-300:]}"
    assert sorted(json.loads(listed.stdout)) == ["db", "redis"]


def test_token_cannot_write_or_wander(vault):
    value, data = vault["token"]()
    assert "error" not in data, data.get("error")
    app = Vault(vault["tmp"], value, "app")
    mount = vault["mount"]
    checks = {
        "ghi olist/api/db": app.run("kv", "put", f"-mount={mount}", "olist/api/db", "password=x"),
        "patch olist/api/db": app.run("kv", "patch", f"-mount={mount}", "olist/api/db", "password=x"),
        "xoá olist/api/db": app.run("kv", "delete", f"-mount={mount}", "olist/api/db"),
        "xoá vĩnh viễn metadata olist/api/db": app.run("kv", "metadata", "delete", f"-mount={mount}", "olist/api/db"),
        "đọc olist/payments/stripe": app.run("kv", "get", f"-mount={mount}", "olist/payments/stripe"),
        "liệt kê olist/": app.run("kv", "list", f"-mount={mount}", "olist"),
        "đọc policy": app.run("policy", "read", vault["policy"]),
        "tạo token con": app.run("token", "create", "-field=accessor"),
    }
    allowed = [what for what, result in checks.items() if not denied(result)]
    assert not allowed, f"Token của api làm được việc ngoài quyền đọc olist/api/*: {allowed}"


def test_token_expires(vault):
    value, data = vault["token"]("4s")
    assert "error" not in data, data.get("error")
    assert data["creation_ttl"] == 4, f"token.sh phải dùng TOKEN_TTL khi được đặt (TOKEN_TTL=4s, đang là {data['creation_ttl']})"
    app = Vault(vault["tmp"], value, "app")
    assert app.run("kv", "get", f"-mount={vault['mount']}", "-field=username", "olist/api/db").returncode == 0
    time.sleep(6)
    late = app.run("kv", "get", f"-mount={vault['mount']}", "-field=username", "olist/api/db")
    assert late.returncode != 0, "Token đã quá TTL mà vẫn đọc được secret"
