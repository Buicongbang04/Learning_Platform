"""M05: infra/ (OpenTofu trên LocalStack) và ansible/ (role olist_worker trên target SSH). Hợp đồng đầy đủ ở
capstone/milestones/m05-iac-config.md."""

import json
import secrets
import shutil
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import pytest
import yaml
from botocore.exceptions import BotoCoreError, ClientError

from olist_stack import APP, missing
from testkit import KUBE_IMAGES, AnsibleLab, Exercise, TofuLab, localstack_client

DOC = "m05-iac-config.md"
ENVIRONMENT = "staging"
STATE_KEY = f"olist-shop/{ENVIRONMENT}/platform.tfstate"
TFVARS = {"environment": ENVIRONMENT, "database_host": "postgres", "redis_host": "redis"}
PARAMS = {"DB_HOST": "postgres", "DB_NAME": "olist", "DB_USER": "olist", "REDIS_URL": "redis://redis:6379/0", "LOG_LEVEL": "INFO"}
TAGS = {"Project": "olist-shop", "Environment": ENVIRONMENT, "ManagedBy": "opentofu"}
HOSTS = ["worker-1", "worker-2"]
NO_DEFAULT = ("prefix", "environment", "database_host", "redis_host", "db_password", "state_passphrase")
HANDLER = "Restart olist-worker"
HOME = "/opt/olist-shop"
ENV_FILE = "/etc/olist-shop/worker.env"
UNIT = "/etc/systemd/system/olist-worker.service"
UNIT_LINES = ["User=olist", "Group=olist", f"EnvironmentFile={ENV_FILE}", f"WorkingDirectory={HOME}/current",
              f"ExecStart={HOME}/.venv/bin/python -m olist_shop.worker", "Restart=on-failure", "NoNewPrivileges=yes",
              "ProtectSystem=strict"]
JOBS = 6
LAUNCHER = r"""
import os, pwd, shlex, sys
service, section = {}, None
for raw in open(sys.argv[1], encoding="utf-8").read().splitlines():
    line = raw.strip()
    if line.startswith("[") and line.endswith("]"):
        section = line[1:-1]
    elif section == "Service" and "=" in line and not line.startswith(("#", ";")):
        key, value = line.split("=", 1)
        service[key.strip()] = value.strip()
env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}
for raw in open(service["EnvironmentFile"].lstrip("-"), encoding="utf-8").read().splitlines():
    line = raw.strip()
    if not line or line.startswith(("#", ";")) or "=" not in line:
        continue
    key, value = line.split("=", 1)
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    env[key.strip()] = value
user = pwd.getpwnam(service["User"])
os.chdir(service["WorkingDirectory"])
os.setgroups([])
os.setgid(user.pw_gid)
os.setuid(user.pw_uid)
env.update(HOME=user.pw_dir, USER=user.pw_name)
argv = shlex.split(service["ExecStart"].lstrip("@-:+!"))
os.execve(argv[0], argv, env)
"""
PROBE = r"""
import json, os, urllib.request
out = {"metrics": None, "uids": []}
try:
    text = urllib.request.urlopen("http://127.0.0.1:9101/metrics", timeout=3).read().decode()
    out["metrics"] = sum(float(l.split()[-1]) for l in text.splitlines() if l.startswith("jobs_processed_total "))
except Exception as error:
    out["error"] = str(error)
for pid in [p for p in os.listdir("/proc") if p.isdigit() and int(p) != os.getpid()]:
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode()
        if cmd.split()[1:3] == ["-m", "olist_shop.worker"]:
            status = open(f"/proc/{pid}/status").read()
            out["uids"].append(int(next(l for l in status.splitlines() if l.startswith("Uid:")).split()[1]))
    except OSError:
        pass
print(json.dumps(out))
"""


def make_password(core: str, tail_chars: str = "@:/#%x") -> str:
    return f"Pw{core}{tail_chars}"


def leaks(text: str, password: str, core: str) -> list[str]:
    """Các dạng của mật khẩu xuất hiện trong `text`: nguyên văn, percent-encode (như trong DATABASE_URL), hay phần ngẫu
    nhiên ở giữa (bắt mọi kiểu mã hoá khác). Chỉ trả tên dạng, không trả giá trị."""
    forms = {"nguyên văn": password, "percent-encode": quote(password, safe=""), "phần ngẫu nhiên": core}
    return [name for name, value in forms.items() if value and value in (text or "")]


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def key_matches(value, key_arn: str, key_id: str, aliases: set[str]) -> bool:
    """`value` (KeyId của SSM hay KMSMasterKeyID của S3) trỏ tới đúng khoá: ARN, id, tên alias hay ARN của alias."""
    if not value or not key_arn:
        return False
    value = str(value)
    if value in (key_arn, key_id) or value in aliases:
        return True
    return ":alias/" in value and "alias/" + value.split(":alias/", 1)[1] in aliases


def trust_services(trust: dict) -> set[str]:
    found = set()
    for statement in (trust or {}).get("Statement", []):
        if statement.get("Effect") != "Allow":
            continue
        principal = statement.get("Principal")
        if not isinstance(principal, dict) or set(principal) != {"Service"}:
            found.add(json.dumps(principal, sort_keys=True))
            continue
        services = principal["Service"]
        found |= {services} if isinstance(services, str) else set(services)
    return found


def aws(rule: str, call, *args, **kwargs):
    """Gọi boto3; tài nguyên thiếu hay sai thì fail với quy tắc của đề thay vì lỗi botocore."""
    try:
        return call(*args, **kwargs)
    except (ClientError, BotoCoreError) as error:
        pytest.fail(f"{rule} ({type(error).__name__}: {str(error)[:200]})", pytrace=False)


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


def statements(policy: dict) -> set[tuple[str, str]]:
    found = set()
    for statement in policy.get("Statement", []):
        if statement.get("Effect") != "Allow":
            continue
        actions, resources = statement.get("Action", []), statement.get("Resource", [])
        for action in [actions] if isinstance(actions, str) else actions:
            for resource in [resources] if isinstance(resources, str) else resources:
                found.add((action, resource))
    return found


def role_grants(role: str) -> set[tuple[str, str]]:
    iam = localstack_client("iam")
    found = set()
    for name in iam.list_role_policies(RoleName=role)["PolicyNames"]:
        document = iam.get_role_policy(RoleName=role, PolicyName=name)["PolicyDocument"]
        found |= statements(json.loads(document) if isinstance(document, str) else document)
    for attached in iam.list_attached_role_policies(RoleName=role)["AttachedPolicies"]:
        version = iam.get_policy(PolicyArn=attached["PolicyArn"])["Policy"]["DefaultVersionId"]
        document = iam.get_policy_version(PolicyArn=attached["PolicyArn"], VersionId=version)["PolicyVersion"]["Document"]
        found |= statements(json.loads(document) if isinstance(document, str) else document)
    return found


def read_parameters(path: str) -> dict[str, dict]:
    if not isinstance(path, str) or not path.startswith("/"):
        pytest.fail(f"Đường dẫn tham số SSM phải bắt đầu bằng '/': {path!r}", pytrace=False)
    return aws(f"Không đọc được cây tham số SSM {path}", _read_parameters, path)


def _read_parameters(path: str) -> dict[str, dict]:
    ssm = localstack_client("ssm")
    found = {}
    for page in ssm.get_paginator("get_parameters_by_path").paginate(Path=path, Recursive=True, WithDecryption=True):
        for item in page["Parameters"]:
            found[item["Name"].rsplit("/", 1)[-1]] = item
    described = {}
    for page in ssm.get_paginator("describe_parameters").paginate(
            ParameterFilters=[{"Key": "Path", "Option": "Recursive", "Values": [path]}]):
        for item in page["Parameters"]:
            described[item["Name"].rsplit("/", 1)[-1]] = item
    for key, item in found.items():
        item["KeyId"] = described.get(key, {}).get("KeyId")
    return found


@dataclass
class Infra:
    lab: TofuLab | None = None
    password: str = ""
    core: str = ""
    passphrase: str = ""
    outputs: dict = field(default_factory=dict)
    runtime: dict = field(default_factory=dict)
    apply_output: str = ""
    error: str = ""

    def require(self) -> "Infra":
        if self.error:
            pytest.fail(self.error, pytrace=False)
        return self

    @property
    def state_bucket(self) -> str:
        return f"{self.lab.prefix}-tfstate"

    def name(self, suffix: str) -> str:
        return f"{self.lab.prefix}-{ENVIRONMENT}-{suffix}"


@pytest.fixture(scope="module")
def infra(project_root):
    source = project_root / "infra"
    if not source.is_dir() or not any(source.glob("*.tf")):
        yield Infra(error=missing(source / "main.tf", DOC))
        return
    Exercise.require_tool("tofu", "1.11")
    with TofuLab(source) as lab:
        core = secrets.token_hex(8)
        state = Infra(lab, password=make_password(core), core=core, passphrase=f"olist-capstone-{secrets.token_hex(8)}")
        lab.write("ci.auto.tfvars.json", json.dumps(TFVARS))
        lab.env["TF_VAR_db_password"] = state.password
        lab.env["TF_VAR_state_passphrase"] = state.passphrase
        try:
            s3 = localstack_client("s3")
            s3.create_bucket(Bucket=state.state_bucket)
            s3.put_bucket_versioning(Bucket=state.state_bucket, VersioningConfiguration={"Status": "Enabled"})
            result = lab.init("-no-color", check=False)
            if result.returncode == 0:
                result = lab.apply("-no-color", check=False)
            state.apply_output = f"{result.stdout}\n{result.stderr}"
            if result.returncode != 0:
                state.error = f"tofu init/apply lỗi:\n{tail(result)}"
            else:
                state.outputs = lab.output()
                path = state.outputs.get("parameter_path")
                try:
                    state.runtime = {k: v["Value"] for k, v in read_parameters(path).items()}
                except pytest.fail.Exception:
                    state.runtime = {}
        except pytest.fail.Exception as error:
            state.error = str(error)
        except (ClientError, BotoCoreError) as error:
            state.error = f"LocalStack từ chối khi chuẩn bị bucket state: {error}"
        yield state


def test_m05_tofu_fmt_and_validate(infra):
    lab = infra.require().lab
    fmt = lab.run("fmt", "-check", "-recursive", "-diff", check=False)
    assert fmt.returncode == 0, f"tofu fmt -check -recursive báo tệp chưa định dạng:\n{tail(fmt)}"
    validate = lab.run("validate", "-no-color", check=False)
    assert validate.returncode == 0, f"tofu validate lỗi:\n{tail(validate)}"


def test_m05_state_remote_encrypted(infra):
    state = infra.require()
    assert not (state.lab.workdir / "terraform.tfstate").exists(), "State không được nằm ở local: dùng backend s3"
    s3 = localstack_client("s3")
    try:
        raw = s3.get_object(Bucket=state.state_bucket, Key=STATE_KEY)["Body"].read().decode()
    except s3.exceptions.NoSuchKey:
        pytest.fail(f"Không thấy state ở s3://{state.state_bucket}/{STATE_KEY}: backend s3 với bucket "
                    "\"${{var.prefix}}-tfstate\" và key olist-shop/<environment>/platform.tfstate", pytrace=False)
    try:
        data = json.loads(raw)
    except ValueError:
        data = {}
    assert "encrypted_data" in data and "resources" not in data, (
        "State trên S3 phải được mã hoá phía client bằng khối encryption của OpenTofu (passphrase từ var.state_passphrase)")
    found = leaks(raw, state.password, state.core)
    assert not found, f"Mật khẩu database ({', '.join(found)}) nằm trong state trên S3"
    name = f".devops-ex-{uuid.uuid4().hex[:8]}.tfplan"
    result = state.lab.run("plan", "-input=false", "-no-color", "-lock=false", f"-out={name}", check=False)
    plan_file = state.lab.workdir / name
    try:
        assert result.returncode == 0 and plan_file.is_file(), f"tofu plan -out lỗi:\n{tail(result)}"
        assert not zipfile.is_zipfile(plan_file), (
            "Tệp plan đang là zip đọc được: khối encryption cần cả `plan { method = ..., enforced = true }`")
    finally:
        plan_file.unlink(missing_ok=True)


def test_m05_state_lockfile(infra):
    state = infra.require()
    s3 = localstack_client("s3")
    lock = {"ID": str(uuid.uuid4()), "Operation": "OperationTypeApply", "Who": "ci@runner-7", "Version": "1.13.2",
            "Created": "2026-11-02T01:00:00Z", "Path": STATE_KEY, "Info": ""}
    s3.put_object(Bucket=state.state_bucket, Key=f"{STATE_KEY}.tflock", Body=json.dumps(lock).encode())
    try:
        result = state.lab.plan("-no-color", "-lock-timeout=0s", check=False)
    finally:
        s3.delete_object(Bucket=state.state_bucket, Key=f"{STATE_KEY}.tflock")
    assert result.returncode != 0 and "Error acquiring the state lock" in f"{result.stdout}{result.stderr}", (
        f"Có tệp khoá {STATE_KEY}.tflock mà plan vẫn chạy: backend s3 cần use_lockfile = true\n{tail(result)}")


def test_m05_password_never_in_state_or_plan(infra):
    state = infra.require()
    pulled = state.lab.run("state", "pull", check=False)
    assert pulled.returncode == 0, tail(pulled)
    found = leaks(pulled.stdout, state.password, state.core)
    assert not found, f"Mật khẩu database ({', '.join(found)}) nằm trong state: ghi qua write-only (value_wo) từ biến ephemeral"
    plan = state.lab.plan_json("-no-color")
    found = leaks(json.dumps(plan), state.password, state.core)
    assert not found, f"Mật khẩu database ({', '.join(found)}) nằm trong plan"
    found = leaks(state.apply_output, state.password, state.core)
    assert not found, f"Mật khẩu database ({', '.join(found)}) hiện trong output của apply"


def test_m05_variables(infra):
    state = infra.require()
    plan = state.lab.plan_json("-no-color")
    variables = plan.get("configuration", {}).get("root_module", {}).get("variables", {})
    found = [f"thiếu variable {name}" for name in (*NO_DEFAULT, "log_level", "db_password_version") if name not in variables]
    found += [f"variable {name} không được có default (thiếu thì tofu phải dừng)" for name in NO_DEFAULT
              if "default" in (variables.get(name) or {})]
    if (variables.get("log_level") or {}).get("default") != "INFO":
        found.append("variable log_level mặc định INFO")
    if (variables.get("db_password_version") or {}).get("default") != 1:
        found.append("variable db_password_version mặc định 1")
    for name in ("db_password", "state_passphrase"):
        if (variables.get(name) or {}).get("sensitive") is not True:
            found.append(f"variable {name} phải sensitive = true")
    assert not found, "\n".join(found)


def test_m05_backup_bucket(infra):
    state = infra.require()
    s3 = localstack_client("s3")
    bucket = state.name("backups")
    assert state.outputs.get("backup_bucket") == bucket, f"output backup_bucket phải là {bucket}: {state.outputs}"
    found = []
    aws(f"Không có bucket {bucket}", s3.head_bucket, Bucket=bucket)

    def optional(call, key):
        try:
            return call(Bucket=bucket).get(key) or {}
        except ClientError:
            return {}

    if s3.get_bucket_versioning(Bucket=bucket).get("Status") != "Enabled":
        found.append("versioning phải Enabled (khôi phục được bản backup bị ghi đè hay xoá)")
    block = optional(s3.get_public_access_block, "PublicAccessBlockConfiguration")
    if not (len(block) == 4 and all(block.values())):
        found.append(f"chặn đủ 4 cờ public access: {block}")
    rules = optional(s3.get_bucket_encryption, "ServerSideEncryptionConfiguration").get("Rules") or []
    default = rules[0].get("ApplyServerSideEncryptionByDefault", {}) if rules else {}
    key, key_id, aliases = key_identity(state)
    if default.get("SSEAlgorithm") != "aws:kms" or not key_matches(default.get("KMSMasterKeyID"), key, key_id, aliases):
        found.append(f"mã hoá mặc định phải là aws:kms bằng khoá của bạn ({key or 'chưa có output kms_key_arn'}): {default}")
    try:
        lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=bucket)["Rules"]
    except ClientError:
        lifecycle = []
    whole = [r for r in lifecycle if r.get("Status") == "Enabled" and not (r.get("Filter") or {}).get("Prefix")
             and not (r.get("Filter") or {}).get("And") and not (r.get("Filter") or {}).get("Tag")]
    if not any((r.get("NoncurrentVersionExpiration") or {}).get("NoncurrentDays") == 30 for r in whole):
        found.append("lifecycle cho cả bucket: bản cũ (noncurrent) hết hạn sau 30 ngày")
    if not any((r.get("AbortIncompleteMultipartUpload") or {}).get("DaysAfterInitiation") for r in whole):
        found.append("lifecycle cho cả bucket: huỷ multipart upload dở dang (AbortIncompleteMultipartUpload)")
    tags = {t["Key"]: t["Value"] for t in optional(s3.get_bucket_tagging, "TagSet") or []}
    if not TAGS.items() <= tags.items():
        found.append(f"thiếu tag chung {TAGS}, đang có {tags}")
    assert not found, f"Bucket {bucket}:\n" + "\n".join(found)


def key_identity(state) -> tuple[str, str, set[str]]:
    """(ARN, id, tên alias) của khoá trong output `kms_key_arn`; rỗng khi chưa có output hay khoá không tồn tại."""
    key = state.outputs.get("kms_key_arn")
    if not isinstance(key, str) or not key.startswith("arn:"):
        return "", "", set()
    kms = localstack_client("kms")
    try:
        meta = kms.describe_key(KeyId=key)["KeyMetadata"]
        aliases = {a["AliasName"] for a in kms.list_aliases(KeyId=meta["KeyId"]).get("Aliases", [])}
    except ClientError:
        return "", "", set()
    return meta["Arn"], meta["KeyId"], aliases


def test_m05_kms_key(infra):
    state = infra.require()
    kms = localstack_client("kms")
    key = state.outputs.get("kms_key_arn")
    assert isinstance(key, str) and key.startswith("arn:"), f"Cần output kms_key_arn: {state.outputs}"
    meta = aws(f"Output kms_key_arn ({key}) không trỏ tới khoá KMS nào", kms.describe_key, KeyId=key)["KeyMetadata"]
    assert kms.get_key_rotation_status(KeyId=key).get("KeyRotationEnabled") is True, "Khoá KMS cần bật xoay khoá tự động"
    alias = f"alias/{state.name('olist-shop')}"
    aliases = {a["AliasName"]: a.get("TargetKeyId") for a in kms.list_aliases()["Aliases"]}
    assert aliases.get(alias) == meta["KeyId"], f"Cần alias {alias} trỏ tới khoá {meta['KeyId']}: {aliases.get(alias)}"


def test_m05_runtime_parameters(infra):
    state = infra.require()
    path = f"/{state.lab.prefix}/{ENVIRONMENT}/olist-shop"
    assert state.outputs.get("parameter_path") == path, f"output parameter_path phải là {path}: {state.outputs}"
    found = read_parameters(path)
    assert set(found) == {*PARAMS, "DB_PASSWORD"}, f"Tham số dưới {path} phải đúng {sorted({*PARAMS, 'DB_PASSWORD'})}: {sorted(found)}"
    problems = [f"{k}: phải là String '{v}', đang {found[k]['Type']} '{found[k]['Value']}'" for k, v in PARAMS.items()
                if (found[k]["Type"], found[k]["Value"]) != ("String", v)]
    secret = found["DB_PASSWORD"]
    if secret["Type"] != "SecureString" or secret["Value"] != state.password:
        problems.append(f"DB_PASSWORD phải là SecureString chứa đúng mật khẩu truyền vào (đang {secret['Type']})")
    key, key_id, aliases = key_identity(state)
    if not key_matches(secret.get("KeyId"), key, key_id, aliases):
        problems.append(f"DB_PASSWORD phải mã hoá bằng khoá KMS của bạn, không phải khoá mặc định aws/ssm: KeyId {secret.get('KeyId')}")
    assert not problems, "\n".join(problems)


def test_m05_app_role_least_privilege(infra):
    state = infra.require()
    iam = localstack_client("iam")
    role = state.name("olist-app")
    info = aws(f"Không có IAM role {role}", iam.get_role, RoleName=role)["Role"]
    assert state.outputs.get("app_role_arn") == info["Arn"], f"output app_role_arn phải là {info['Arn']}"
    trust = info["AssumeRolePolicyDocument"]
    trust = json.loads(trust) if isinstance(trust, str) else trust
    assert trust_services(trust) == {"ec2.amazonaws.com"}, (
        f"Role {role} là instance role: chỉ đúng ec2.amazonaws.com được assume: {trust}")
    account = localstack_client("sts").get_caller_identity()["Account"]
    params = f"arn:aws:ssm:us-east-1:{account}:parameter/{state.lab.prefix}/{ENVIRONMENT}/olist-shop"
    key = state.outputs.get("kms_key_arn")
    bucket = f"arn:aws:s3:::{state.name('backups')}"
    expected = {("ssm:GetParameter", f"{params}/*"), ("ssm:GetParameters", f"{params}/*"),
                ("ssm:GetParametersByPath", params), ("kms:Decrypt", key), ("kms:GenerateDataKey", key),
                ("s3:PutObject", f"{bucket}/*")}
    found = role_grants(role)
    assert found == expected, (f"Quyền của {role} phải đúng bằng danh sách trong đề.\nThừa: {sorted(found - expected)}\n"
                               f"Thiếu: {sorted(expected - found)}")


def test_m05_second_plan_has_no_changes(infra):
    state = infra.require()
    result = state.lab.plan("-no-color", "-detailed-exitcode", check=False)
    assert result.returncode == 0, f"Plan lần hai phải 'No changes' (mã 0), nhận mã {result.returncode}:\n{tail(result)}"


def test_m05_rejects_bad_log_level(infra):
    state = infra.require()
    path = state.lab.write("zz-bad.auto.tfvars.json", json.dumps({"log_level": "TRACE"}))
    try:
        result = state.lab.plan("-no-color", check=False)
    finally:
        path.unlink()
    assert result.returncode != 0 and "Invalid value for variable" in f"{result.stdout}{result.stderr}", (
        f"log_level TRACE phải bị chặn bằng validation của biến:\n{tail(result)}")


@dataclass
class Fleet:
    lab: AnsibleLab | None = None
    project: Path | None = None
    runs: dict = field(default_factory=dict)
    snapshots: dict = field(default_factory=dict)
    jobs: dict = field(default_factory=dict)
    password: str = ""
    core: str = ""
    error: str = ""

    def require(self) -> "Fleet":
        if self.error:
            pytest.fail(self.error, pytrace=False)
        return self

    def run(self, name: str):
        self.require()
        run = self.runs.get(name)
        if run is None:
            pytest.fail(f"Chưa tới lần chạy {name}: {self.error or 'lần chạy trước đó lỗi'}", pytrace=False)
        return run


def release_args(release: str) -> list[str]:
    return ["-e", "@runtime.json", "-e", f"olist_worker_release={release}"]


def snapshot(lab: AnsibleLab) -> dict:
    found = {}
    for host in HOSTS:
        found[host] = {"current": lab.exec(host, "readlink", f"{HOME}/current").stdout.strip(),
                       "config": lab.stat(host, "/etc/olist-shop") is not None,
                       "install": lab.stat(host, HOME) is not None,
                       "env": lab.read(host, ENV_FILE)}
    return found


def run_workers(lab: AnsibleLab) -> dict:
    for host in HOSTS:
        start = lab.exec(host, "sh", "-c", f'setsid /usr/local/bin/python3 -c "$1" {UNIT} >/var/log/devops-ex-worker.log '
                         '2>&1 </dev/null &', "launcher", LAUNCHER)
        if start.returncode != 0:
            return {"error": f"{host}: không khởi chạy được worker theo unit: {start.stderr}"}
    probes = {}
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        probes = {host: json.loads(lab.exec(host, "/usr/local/bin/python3", "-c", PROBE).stdout or "{}") for host in HOSTS}
        if all(p.get("metrics") is not None for p in probes.values()):
            break
        time.sleep(1)
    else:
        logs = {host: (lab.read(host, "/var/log/devops-ex-worker.log") or "")[-1500:] for host in HOSTS}
        return {"error": f"Worker chạy theo unit không lên (metrics :9101) sau 60 giây: {probes}\n{logs}"}
    for index in range(JOBS):
        before = sum(p["metrics"] for p in probes.values())
        payload = json.dumps({"job_id": f"m05-{index}-{uuid.uuid4().hex[:6]}", "type": "recompute_revenue"})
        lab.docker.exec("redis", "redis-cli", "RPUSH", "olist:jobs", payload)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            probes = {host: json.loads(lab.exec(host, "/usr/local/bin/python3", "-c", PROBE).stdout or "{}") for host in HOSTS}
            if sum(p.get("metrics") or 0 for p in probes.values()) > before:
                break
            time.sleep(0.5)
    logs = {host: lab.read(host, "/var/log/devops-ex-worker.log") or "" for host in HOSTS}
    return {"probes": probes, "logs": logs}


@pytest.fixture(scope="module")
def fleet(project_root, infra):
    source = project_root / "ansible"
    if not (source / "site.yml").is_file():
        yield Fleet(error=missing(source / "site.yml", DOC))
        return
    if infra.error:
        yield Fleet(error=f"Phần Ansible dùng cấu hình runtime do infra/ ghi lên SSM; sửa infra/ trước:\n{infra.error}")
        return
    if set(infra.runtime) != {*PARAMS, "DB_PASSWORD"}:
        yield Fleet(error=f"Cây tham số SSM do infra/ tạo chưa đủ {sorted({*PARAMS, 'DB_PASSWORD'})}: {sorted(infra.runtime)}")
        return
    for image in ("postgres", "redis"):
        Exercise.require_image(KUBE_IMAGES[image])
    runtime = dict(infra.runtime)
    with AnsibleLab(HOSTS) as lab:
        state = Fleet(lab, password=runtime["DB_PASSWORD"], core=infra.core)
        try:
            lab.docker.start("postgres", KUBE_IMAGES["postgres"], env={
                "POSTGRES_USER": runtime["DB_USER"], "POSTGRES_PASSWORD": runtime["DB_PASSWORD"],
                "POSTGRES_DB": runtime["DB_NAME"]})
            lab.docker.start("redis", KUBE_IMAGES["redis"])
            project = state.project = lab.stage(source)
            shutil.copytree(APP / "olist_shop", project / "artifacts" / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
            (project / "runtime.json").write_text(json.dumps({"olist_worker_runtime": runtime}), encoding="utf-8")
            lab.docker.wait_log("postgres", "database system is ready to accept connections", timeout=60)
            first, second = f"m05-{uuid.uuid4().hex[:8]}", f"m05-{uuid.uuid4().hex[:8]}"
            state.runs["releases"] = (first, second)
            state.runs["missing"] = lab.playbook("site.yml", inventory=["inventory"], cwd=project)
            state.snapshots["missing"] = snapshot(lab)
            state.runs["first"] = lab.playbook("site.yml", *release_args(first), "--diff", "-v", inventory=["inventory"],
                                               cwd=project)
            if state.runs["first"].returncode == 0:
                state.runs["second"] = lab.playbook("site.yml", *release_args(first), inventory=["inventory"], cwd=project)
                state.runs["check"] = lab.playbook("site.yml", *release_args(first), "--check", "--diff",
                                                   inventory=["inventory"], cwd=project)
                state.snapshots["first"] = snapshot(lab)
                state.jobs = run_workers(lab)
                state.runs["upgrade"] = lab.playbook("site.yml", *release_args(second), "--diff", "-v",
                                                     inventory=["inventory"], cwd=project)
                state.snapshots["upgrade"] = snapshot(lab)
        except pytest.fail.Exception as error:
            state.error = str(error)
        yield state


def converged(fleet: Fleet):
    first = fleet.run("first")
    assert first.returncode == 0, f"Lần chạy đầu lỗi:\n{first.tail()}"
    assert set(first.recap) == set(HOSTS) and all(first.recap[h]["failures"] == 0 for h in HOSTS), first.recap
    return fleet.lab, first


def test_m05_role_layout(project_root):
    role = project_root / "ansible" / "roles" / "olist_worker"
    files = ["defaults/main.yml", "tasks/main.yml", "handlers/main.yml", "meta/main.yml", "meta/argument_specs.yml",
             "templates/worker.env.j2", "templates/olist-worker.service.j2"]
    lacking = [rel for rel in files if not (role / rel).is_file()]
    assert not lacking, f"Role ansible/roles/olist_worker thiếu {lacking}. Xem tracks/devops/capstone/milestones/{DOC}"
    spec = yaml.safe_load((role / "meta" / "argument_specs.yml").read_text(encoding="utf-8")) or {}
    options = ((spec.get("argument_specs") or {}).get("main") or {}).get("options") or {}
    for name in ("olist_worker_release", "olist_worker_runtime"):
        assert (options.get(name) or {}).get("required") is True, f"argument_specs: {name} phải required: true"
    runtime = (options.get("olist_worker_runtime") or {}).get("options") or {}
    lacking = [k for k in (*PARAMS, "DB_PASSWORD") if (runtime.get(k) or {}).get("required") is not True]
    assert not lacking, f"argument_specs: olist_worker_runtime cần options required cho {lacking}"
    assert (runtime.get("DB_PASSWORD") or {}).get("no_log") is True, "argument_specs: DB_PASSWORD cần no_log: true"


def test_m05_missing_inputs_change_nothing(fleet):
    run = fleet.run("missing")
    assert run.returncode != 0, "Thiếu olist_worker_release và olist_worker_runtime thì playbook phải dừng"
    assert not run.tasks(changed=True), f"Thiếu đầu vào mà vẫn có task đổi máy: {sorted({t['task'] for t in run.tasks(changed=True)})}"
    touched = {h: s for h, s in fleet.snapshots["missing"].items() if s["config"] or s["install"]}
    assert not touched, f"Thiếu đầu vào mà host đã bị đổi: {touched}"


def test_m05_first_run_converges(fleet):
    _, first = converged(fleet)
    notified = {t["host"] for t in first.tasks(HANDLER, handler=True)}
    assert notified == set(HOSTS), f"Handler '{HANDLER}' phải chạy trên mọi host ở lần đầu, chỉ thấy {notified}"


def test_m05_rolls_one_host_at_a_time(fleet):
    _, first = converged(fleet)
    order = [t["host"] for t in first.tasks() if t["task"] not in ("Gathering Facts", "gather_facts")]
    last_first = max(i for i, h in enumerate(order) if h == HOSTS[0])
    first_second = min(i for i, h in enumerate(order) if h == HOSTS[1])
    assert last_first < first_second, "Play phải chạy từng host một (serial: 1): một host hỏng thì host còn lại vẫn chạy bản cũ"


def test_m05_secret_never_printed(fleet):
    for name in ("missing", "first", "upgrade"):
        found = leaks(fleet.run(name).output, fleet.password, fleet.core)
        assert not found, (f"Lần chạy {name} (--diff -v) in mật khẩu database ra output ({', '.join(found)}; DATABASE_URL "
                           "chứa bản percent-encode): dùng no_log và diff: false cho task ghi env file")


def test_m05_release_layout(fleet):
    lab, _ = converged(fleet)
    release = fleet.runs["releases"][0]
    for host in HOSTS:
        passwd = lab.exec(host, "getent", "passwd", "olist").stdout.strip().split(":")
        assert len(passwd) == 7 and int(passwd[2]) < 1000 and passwd[6] == "/usr/sbin/nologin", f"{host}: cần user hệ thống olist: {passwd}"
        assert lab.stat(host, f"{HOME}/releases/{release}/olist_shop/worker.py") == ("644", "root", "root")
        assert fleet.snapshots["first"][host]["current"] == f"{HOME}/releases/{release}", (
            f"{host}: {HOME}/current phải là symlink tới {HOME}/releases/{release}")
        assert lab.stat(host, f"{HOME}/.venv/bin/python") is not None, f"{host}: thiếu virtualenv {HOME}/.venv"


def env_lines(text: str | None) -> dict[str, str]:
    """Đọc env file như `EnvironmentFile=` của systemd: bỏ dòng trống, dòng `#`/`;`, bỏ một cặp nháy bao ngoài giá trị."""
    pairs = [line.split("=", 1) for line in (text or "").splitlines()
             if "=" in line and not line.lstrip().startswith(("#", ";"))]
    return {key.strip(): strip_quotes(value) for key, value in pairs}


def test_m05_env_file_from_ssm(fleet):
    lab, _ = converged(fleet)
    release = fleet.runs["releases"][0]
    for host in HOSTS:
        assert lab.stat(host, ENV_FILE) == ("640", "root", "olist"), f"{host}: {ENV_FILE} phải 0640 root:olist"
        env = env_lines(fleet.snapshots["first"][host]["env"])
        assert set(env) == {"DATABASE_URL", "REDIS_URL", "LOG_LEVEL", "APP_VERSION"}, f"{host}: khoá của {ENV_FILE}: {sorted(env)}"
        assert (env["REDIS_URL"], env["LOG_LEVEL"], env["APP_VERSION"]) == (PARAMS["REDIS_URL"], PARAMS["LOG_LEVEL"], release)
        url = urlsplit(env["DATABASE_URL"])
        try:
            port = url.port
        except ValueError:
            port = None
        shape = (url.scheme, url.username, url.hostname, port, url.path)
        password_ok = unquote(url.password or "") == fleet.password
        ok = shape == ("postgresql+psycopg", "olist", "postgres", 5432, "/olist") and password_ok
        assert ok, (f"{host}: DATABASE_URL phải dựng từ DB_USER, DB_PASSWORD (percent-encode), DB_HOST, DB_NAME: đọc ra "
                    f"{shape}, mật khẩu {'đúng' if password_ok else 'sai'}")


def test_m05_unit_file_verified(fleet):
    lab, _ = converged(fleet)
    for host in HOSTS:
        assert lab.stat(host, UNIT) == ("644", "root", "root")
        text = lab.read(host, UNIT) or ""
        lines = [l.strip().replace(" = ", "=") for l in text.splitlines()]
        lacking = [l for l in UNIT_LINES if l not in lines]
        assert not lacking, f"{host}: {UNIT} thiếu {lacking}"
        result = lab.exec(host, "systemd-analyze", "verify", "--man=no", UNIT)
        assert result.returncode == 0, f"{host}: systemd-analyze verify lỗi:\n{result.stdout}{result.stderr}"


def test_m05_second_run_and_check_change_nothing(fleet):
    converged(fleet)
    for name in ("second", "check"):
        run = fleet.run(name)
        assert run.returncode == 0 and run.changed == {h: 0 for h in HOSTS}, (
            f"Lần chạy {name} phải changed=0, nhận {run.changed}; task còn đổi: "
            f"{sorted({t['task'] for t in run.tasks(changed=True)})}\n{run.tail(20)}")
        assert not run.tasks(HANDLER, handler=True), f"Lần chạy {name} không đổi gì thì handler không được chạy"


def test_m05_workers_process_shared_queue(fleet):
    converged(fleet)
    jobs = fleet.jobs
    assert not jobs.get("error"), jobs.get("error")
    probes = jobs["probes"]
    counts = {h: probes[h].get("metrics") for h in HOSTS}
    assert sum(c or 0 for c in counts.values()) == JOBS, f"Hai worker phải xử lý đủ {JOBS} job từ cùng hàng đợi: {counts}"
    assert all((c or 0) >= 1 for c in counts.values()), f"Mỗi worker phải nhận job (cùng Redis, cùng queue): {counts}"
    for host in HOSTS:
        assert probes[host]["uids"] and 0 not in probes[host]["uids"], f"{host}: worker phải chạy bằng user olist, không root"
        assert "job done" in jobs["logs"][host], f"{host}: log worker không có 'job done':\n{jobs['logs'][host][-800:]}"


def test_m05_upgrade_switches_release(fleet):
    lab, _ = converged(fleet)
    run = fleet.run("upgrade")
    first, second = fleet.runs["releases"]
    assert run.returncode == 0, run.tail()
    assert {t["host"] for t in run.tasks(HANDLER, handler=True)} == set(HOSTS), "Release mới phải notify handler trên mọi host"
    for host in HOSTS:
        assert fleet.snapshots["upgrade"][host]["current"] == f"{HOME}/releases/{second}", f"{host}: current chưa sang {second}"
        assert lab.stat(host, f"{HOME}/releases/{first}/olist_shop/worker.py") is not None, (
            f"{host}: release cũ {first} phải còn để rollback bằng cách chạy lại với release cũ")
        assert env_lines(fleet.snapshots["upgrade"][host]["env"]).get("APP_VERSION") == second


def test_m05_password_rotation(infra):
    state = infra.require()
    lab = state.lab
    core = secrets.token_hex(8)
    new = make_password(core, "@:/#%y")
    lab.env["TF_VAR_db_password"] = new
    lab.env["TF_VAR_db_password_version"] = "2"
    plan = lab.plan_json("-no-color")
    changes = {r["address"]: r["change"]["actions"] for r in plan["resource_changes"]
               if r["change"]["actions"] not in (["no-op"], ["read"])}
    assert len(changes) == 1 and list(changes.values()) == [["update"]], (
        f"Xoay mật khẩu (db_password_version = 2) chỉ được cập nhật tại chỗ đúng tham số DB_PASSWORD: {changes}")
    result = lab.apply("-no-color", check=False)
    assert result.returncode == 0, tail(result)
    value = read_parameters(f"/{lab.prefix}/{ENVIRONMENT}/olist-shop")["DB_PASSWORD"]["Value"]
    rotated = value == new
    assert rotated, "Sau khi xoay, DB_PASSWORD trên SSM phải là mật khẩu mới"
    found = leaks(lab.run("state", "pull").stdout, new, core)
    assert not found, f"Mật khẩu mới ({', '.join(found)}) nằm trong state"


def test_m05_helpers_catch_mistakes():
    """Các phép kiểm thuần, không cần LocalStack hay target: dạng mật khẩu bị lộ, env file có nháy, khoá KMS qua alias,
    trust policy thừa principal, lỗi boto3 thành fail có quy tắc."""
    core = "0123456789abcdef"
    password = make_password(core)
    assert leaks(f"DATABASE_URL=postgresql+psycopg://olist:{quote(password, safe='')}@db/olist", password, core) == [
        "percent-encode", "phần ngẫu nhiên"]
    assert leaks(f"x {password} y", password, core)[0] == "nguyên văn"
    assert leaks("không có gì", password, core) == []
    assert env_lines('# c\n; c\nA="x y"\nB=\'z\'\nC= v \n') == {"A": "x y", "B": "z", "C": "v"}
    arn, key_id = "arn:aws:kms:us-east-1:000000000000:key/k1", "k1"
    aliases = {"alias/p-staging-olist-shop"}
    assert key_matches("arn:aws:kms:us-east-1:000000000000:alias/p-staging-olist-shop", arn, key_id, aliases)
    assert key_matches("alias/p-staging-olist-shop", arn, key_id, aliases) and key_matches("k1", arn, key_id, aliases)
    assert not key_matches("alias/aws/ssm", arn, key_id, aliases) and not key_matches(None, arn, key_id, aliases)
    allow = lambda principal: {"Statement": [{"Effect": "Allow", "Principal": principal, "Action": "sts:AssumeRole"}]}
    assert trust_services(allow({"Service": "ec2.amazonaws.com"})) == {"ec2.amazonaws.com"}
    assert trust_services(allow({"Service": ["ec2.amazonaws.com", "lambda.amazonaws.com"]})) != {"ec2.amazonaws.com"}
    assert trust_services(allow({"AWS": "*", "Service": "ec2.amazonaws.com"})) != {"ec2.amazonaws.com"}

    def denied():
        raise ClientError({"Error": {"Code": "NoSuchEntity", "Message": "x"}}, "GetRole")

    with pytest.raises(pytest.fail.Exception, match="Không có IAM role"):
        aws("Không có IAM role r", denied)
    with pytest.raises(pytest.fail.Exception, match="bắt đầu bằng"):
        read_parameters("devops-ex-x/staging/olist-shop")
