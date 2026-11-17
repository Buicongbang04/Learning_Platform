import json
from pathlib import Path

import pytest

from testkit import Exercise, TofuLab, localstack_client

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
PASSWORD = "olist-db-Pa55word-2026"
VARS = {
    "environment": "staging",
    "expected_account_id": "000000000000",
    "services": {
        "api": {"port": 8000, "replicas": 2, "public": True, "settings": {"LOG_LEVEL": "info", "WORKERS": "4"}},
        "worker": {"port": 9000, "replicas": 1, "settings": {"QUEUE": "orders"}},
        "web": {"port": 3000, "replicas": 2, "public": True},
    },
    "retention": [{"prefix": "nginx/", "days": 30}, {"prefix": "snapshots/", "days": 7}],
}
UPSTREAMS = "upstream api {\n  server api:8000;\n}\nupstream web {\n  server web:3000;\n}\n"


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


def text(result) -> str:
    return f"{result.stdout}\n{result.stderr}"


@pytest.fixture(scope="module")
def lab():
    ex.require_tool("tofu", "1.11")
    with TofuLab(ex.path("infra")) as lab:
        lab.env["TF_VAR_db_password"] = PASSWORD
        lab.write("ci.auto.tfvars.json", json.dumps(VARS))
        result = lab.init("-no-color", check=False)
        if result.returncode == 0:
            result = lab.apply("-no-color", check=False)
        yield lab, result


@pytest.fixture(scope="module")
def applied(lab):
    tofu, result = lab
    assert result.returncode == 0, f"init/apply lỗi:\n{tail(result)}"
    return tofu


def plan_with(tofu, override: dict, *args: str):
    path = tofu.write("zz-case.auto.tfvars.json", json.dumps({**VARS, **override}))
    try:
        return tofu.plan("-no-color", *args, check=False)
    finally:
        path.unlink()


def test_fmt_and_validate(lab):
    tofu, _ = lab
    fmt = tofu.run("fmt", "-check", "-recursive", "-diff", check=False)
    assert fmt.returncode == 0, f"tofu fmt -check -recursive báo tệp chưa định dạng:\n{tail(fmt)}"
    validate = tofu.run("validate", "-no-color", check=False)
    assert validate.returncode == 0, f"tofu validate lỗi:\n{tail(validate)}"


def test_settings_in_parameter_store(applied):
    ssm = localstack_client("ssm")
    base = f"/{applied.prefix}/staging"
    expected = {f"{base}/api/LOG_LEVEL": "info", f"{base}/api/WORKERS": "4", f"{base}/worker/QUEUE": "orders"}
    found = {}
    for page in ssm.get_paginator("get_parameters_by_path").paginate(Path=base, Recursive=True):
        for parameter in page["Parameters"]:
            if parameter["Type"] == "String":
                found[parameter["Name"]] = parameter["Value"]
    assert found == expected, f"Tham số String dưới {base}: {found}"


def test_password_is_secure_string(applied):
    ssm = localstack_client("ssm")
    name = f"/{applied.prefix}/staging/db/password"
    parameter = ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]
    assert parameter["Type"] == "SecureString", f"{name} phải là SecureString"
    assert parameter["Value"] == PASSWORD, f"{name} không chứa đúng giá trị của var.db_password"


def secret_in_state(tofu) -> bool:
    return PASSWORD in tofu.state("pull").stdout


def test_password_never_in_state_or_output(lab, applied):
    _, result = lab
    assert "aws_ssm_parameter.db_password" in applied.state("list").stdout.split(), "Chưa có aws_ssm_parameter.db_password"
    assert not secret_in_state(applied), "Mật khẩu nằm trong state: dùng thuộc tính write-only (value_wo) với biến ephemeral"
    assert PASSWORD not in text(result), "Mật khẩu bị in ra output của apply"
    assert PASSWORD not in json.dumps(applied.output()), "Mật khẩu nằm trong output"


def test_check_catches_sensitive_only_secret():
    ex.require_tool("tofu", "1.11")
    with TofuLab(FIXTURES / "sensitive-only") as tofu:
        tofu.env["TF_VAR_db_password"] = PASSWORD
        tofu.init()
        tofu.apply()
        assert secret_in_state(tofu), "Bản chỉ đánh dấu sensitive phải để lộ mật khẩu trong state (sensitive chỉ che output)"


def test_upstreams_rendered_from_template(applied):
    s3 = localstack_client("s3")
    body = s3.get_object(Bucket=f"{applied.prefix}-staging-runtime-config", Key="nginx/upstreams.conf")["Body"].read().decode()
    assert body == UPSTREAMS, f"nginx/upstreams.conf phải đúng:\n{UPSTREAMS}\nđang là:\n{body}"


def test_lifecycle_rules_from_list(applied):
    s3 = localstack_client("s3")
    rules = s3.get_bucket_lifecycle_configuration(Bucket=f"{applied.prefix}-staging-runtime-config")["Rules"]
    found = sorted((r["ID"], r.get("Filter", {}).get("Prefix"), r["Expiration"]["Days"], r["Status"]) for r in rules)
    assert found == [("expire-nginx", "nginx/", 30, "Enabled"), ("expire-snapshots", "snapshots/", 7, "Enabled")], found


def test_outputs(applied):
    outputs = applied.output()
    base = f"/{applied.prefix}/staging"
    assert outputs.get("parameter_names") == [f"{base}/api/LOG_LEVEL", f"{base}/api/WORKERS", f"{base}/worker/QUEUE"]
    assert outputs.get("public_services") == ["api", "web"]
    assert outputs.get("db_password_parameter") == f"{base}/db/password"
    assert outputs.get("account_id") == "000000000000"


def test_second_plan_has_no_changes(applied):
    assert applied.output().get("parameter_names"), "Chưa có tham số nào được tạo"
    result = applied.plan("-no-color", "-detailed-exitcode", check=False)
    assert result.returncode == 0, f"Plan lần hai phải 'No changes' (mã 0), nhận mã {result.returncode}:\n{tail(result)}"


@pytest.mark.parametrize("port", [80, 70000])
def test_validation_rejects_bad_port(applied, port):
    services = {**VARS["services"], "api": {**VARS["services"]["api"], "port": port}}
    result = plan_with(applied, {"services": services})
    assert result.returncode != 0 and "Invalid value for variable" in text(result), (
        f"Cổng {port} phải bị validation của services chặn:\n{tail(result)}")


def test_validation_rejects_short_password(applied):
    applied.env["TF_VAR_db_password"] = "ngan-qua"
    try:
        result = applied.plan("-no-color", check=False)
    finally:
        applied.env["TF_VAR_db_password"] = PASSWORD
    assert result.returncode != 0 and "Invalid value for variable" in text(result), (
        f"Mật khẩu dưới 16 ký tự phải bị validation chặn:\n{tail(result)}")
    assert "ngan-qua" not in text(result), "Biến nhạy cảm bị in ra trong thông báo lỗi"


def test_precondition_needs_public_service(applied):
    services = {key: {**value, "public": False} for key, value in VARS["services"].items()}
    result = plan_with(applied, {"services": services})
    assert result.returncode != 0 and "Resource precondition failed" in text(result), (
        f"Không có service public nào thì precondition của aws_s3_object phải chặn plan:\n{tail(result)}")


def test_postcondition_guards_account(applied):
    result = plan_with(applied, {"expected_account_id": "111111111111"})
    assert result.returncode != 0 and "Resource postcondition failed" in text(result), (
        f"Sai tài khoản thì postcondition của data.aws_caller_identity phải chặn plan:\n{tail(result)}")


def test_check_block_warns_only(lab, applied):
    _, result = lab
    assert "Check block assertion failed" not in text(result), "staging không được kích hoạt cảnh báo của check"
    prod = plan_with(applied, {"environment": "prod"}, "-detailed-exitcode")
    assert prod.returncode in (0, 2), f"check chỉ cảnh báo, không được làm plan lỗi:\n{tail(prod)}"
    assert "Check block assertion failed" in text(prod), "prod có worker 1 replica mà check không cảnh báo"
