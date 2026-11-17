import re

import pytest
import yaml

from testkit import AnsibleLab, Exercise

ex = Exercise(__file__)
HOSTS = ["worker-1", "worker-2"]
VAULT_PASSWORD = "olist-lab-vault-2026"
VAULT_FILE = "inventory/group_vars/workers/vault.yml"
VARS_FILE = "inventory/group_vars/workers/vars.yml"
WORKER2 = "inventory/host_vars/worker-2.yml"
HEADER = "$ANSIBLE_VAULT;1.2;AES256;prod"
DB = "Olist-Db-2026!x7"
REDIS = "Olist-Redis-2026!k3"
REDIS_W2 = "Olist-Redis-W2!q9"
ROTATED = "Olist-Db-ROTATED!z1"
SECRETS = "/etc/olist-shop/secrets.env"
EXPECTED = {
    "worker-1": f"DATABASE_PASSWORD={DB}\nREDIS_PASSWORD={REDIS}\n",
    "worker-2": f"DATABASE_PASSWORD={DB}\nREDIS_PASSWORD={REDIS_W2}\n",
}


@pytest.fixture(scope="module")
def lab():
    with AnsibleLab(HOSTS) as lab:
        project = lab.stage(ex.target)
        good = lab.write("vault-pass/prod", f"{VAULT_PASSWORD}\n")
        bad = lab.write("vault-pass/wrong", "khong-phai-mat-khau\n")
        good.chmod(0o600)
        bad.chmod(0o600)
        runs = {
            "view": lab.run("ansible-vault", "view", "--vault-id", f"prod@{good}", VAULT_FILE, cwd=project),
            "first": lab.playbook("site.yml", "--diff", "-v", "--vault-id", f"prod@{good}", inventory=["inventory"], cwd=project),
            "second": lab.playbook("site.yml", "--diff", "--vault-id", f"prod@{good}", inventory=["inventory"], cwd=project),
        }
        runs["contents"] = {host: lab.read(host, SECRETS) for host in HOSTS}
        runs["modes"] = {host: lab.stat(host, SECRETS) for host in HOSTS}
        runs["rotate"] = lab.playbook("site.yml", "--diff", "-v", "--vault-id", f"prod@{good}", "-e",
                                      f"vault_olist_db_password={ROTATED}", inventory=["inventory"], cwd=project)
        runs["rotated"] = lab.read("worker-1", SECRETS)
        runs["wrong"] = lab.playbook("site.yml", "--vault-id", f"prod@{bad}", inventory=["inventory"], cwd=project)
        yield runs


def first_line(rel: str) -> str:
    return (ex.read(rel).splitlines() or [""])[0].strip()


def test_vault_file_encrypted_with_prod_id():
    assert first_line(VAULT_FILE) == HEADER, (
        f"{VAULT_FILE} phải được mã hoá cả tệp bằng vault id prod (dòng đầu {HEADER}), đang là {first_line(VAULT_FILE)!r}")


def test_vault_content(lab):
    view = lab["view"]
    assert view.returncode == 0, f"ansible-vault view với mật khẩu của bài lỗi:\n{view.stderr}"
    assert yaml.safe_load(view.stdout) == {"vault_olist_db_password": DB, "vault_olist_redis_password": REDIS}


def test_worker2_uses_encrypt_string():
    text = ex.read(WORKER2)
    assert not text.startswith("$ANSIBLE_VAULT"), f"{WORKER2} giữ dạng YAML thường, chỉ mã hoá một giá trị (encrypt_string)"
    assert re.search(r"^vault_olist_redis_password:\s*!vault\s*\|", text, re.M), "Giá trị phải có tag !vault"
    assert HEADER in text, f"Giá trị !vault phải mã hoá bằng vault id prod ({HEADER})"


def test_vars_point_to_vault():
    data = yaml.safe_load(ex.read(VARS_FILE)) or {}
    normalized = {key: re.sub(r"\s+", "", str(value)) for key, value in data.items()}
    assert normalized == {"olist_db_password": "{{vault_olist_db_password}}",
                          "olist_redis_password": "{{vault_olist_redis_password}}"}, (
        f"{VARS_FILE} chỉ trỏ tên biến thường sang biến vault_*: {data}")


def test_no_plaintext_secret_in_repo():
    root = ex.path(".")
    leaks = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            text = path.read_text(encoding="utf-8", errors="replace")
            leaks += [f"{path.relative_to(root)}: {secret}" for secret in (DB, REDIS, REDIS_W2) if secret in text]
    assert not leaks, "Bí mật còn ở dạng rõ trong repo:\n" + "\n".join(leaks)


def test_deploys_secrets(lab):
    first = lab["first"]
    assert first.returncode == 0, first.tail()
    for host in HOSTS:
        assert lab["contents"][host] == EXPECTED[host], f"{host}: nội dung {SECRETS} sai"
        assert lab["modes"][host] == ("640", "root", "olist"), f"{host}: {SECRETS} phải 0640 root:olist"


def test_secrets_never_printed(lab):
    first, rotate = lab["first"], lab["rotate"]
    assert first.returncode == 0 and rotate.returncode == 0, rotate.tail()
    for name, run in (("--diff -v lần đầu", first), ("--diff -v khi xoay mật khẩu", rotate)):
        leaked = [s for s in (DB, REDIS, REDIS_W2, ROTATED) if s in run.output]
        assert not leaked, f"Output của {name} lộ bí mật {leaked}"
    assert lab["rotated"] == f"DATABASE_PASSWORD={ROTATED}\nREDIS_PASSWORD={REDIS}\n", "Xoay mật khẩu phải ghi giá trị mới"


def test_second_run_idempotent(lab):
    second = lab["second"]
    assert lab["first"].returncode == 0 and second.returncode == 0, second.tail()
    assert second.changed == {h: 0 for h in HOSTS}, second.changed


def test_wrong_password_fails_without_leak(lab):
    wrong = lab["wrong"]
    assert wrong.returncode != 0, "Sai mật khẩu vault mà playbook vẫn chạy: tệp vault chưa được dùng"
    assert "Decryption failed" in wrong.output or "no vault secrets" in wrong.output.lower(), wrong.tail()
    assert not [s for s in (DB, REDIS, REDIS_W2) if s in wrong.output]
