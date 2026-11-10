import json

import pytest

from testkit import Exercise, TofuLab, localstack_client

ex = Exercise(__file__)
VARS = {
    "environment": "staging",
    "buckets": {"media": {}, "exports": {"versioning": False}, "invoices": {}},
    "services": {
        "api": {"read": ["media", "invoices"], "write": ["media"]},
        "worker": {"read": ["exports"], "write": ["exports", "invoices"]},
    },
}
TAGS = {"Project": "olist-shop", "Environment": "staging", "ManagedBy": "opentofu"}
BAD_INPUTS = {
    "environment-prd": {"environment": "prd"},
    "bucket-key-uppercase": {"buckets": {"Media_Files": {}}},
    "service-unknown-bucket": {"buckets": {"media": {}}, "services": {"api": {"read": ["media", "khong-co"]}}},
}


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


@pytest.fixture(scope="module")
def lab():
    with TofuLab(ex.path("infra")) as lab:
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


def name(tofu, key: str) -> str:
    return f"{tofu.prefix}-staging-{key}"


def grants(policy: dict) -> set[tuple[str, str]]:
    found = set()
    for statement in policy.get("Statement", []):
        if statement.get("Effect") != "Allow":
            continue
        actions = statement.get("Action", [])
        resources = statement.get("Resource", [])
        for action in [actions] if isinstance(actions, str) else actions:
            for resource in [resources] if isinstance(resources, str) else resources:
                found.add((action, resource))
    return found


def role_grants(role: str) -> set[tuple[str, str]]:
    iam = localstack_client("iam")
    found = set()
    for policy in iam.list_role_policies(RoleName=role)["PolicyNames"]:
        document = iam.get_role_policy(RoleName=role, PolicyName=policy)["PolicyDocument"]
        found |= grants(json.loads(document) if isinstance(document, str) else document)
    for attached in iam.list_attached_role_policies(RoleName=role)["AttachedPolicies"]:
        version = iam.get_policy(PolicyArn=attached["PolicyArn"])["Policy"]["DefaultVersionId"]
        document = iam.get_policy_version(PolicyArn=attached["PolicyArn"], VersionId=version)["PolicyVersion"]["Document"]
        found |= grants(json.loads(document) if isinstance(document, str) else document)
    return found


def expected_grants(tofu, service: str) -> set[tuple[str, str]]:
    spec = VARS["services"][service]
    arn = lambda key: f"arn:aws:s3:::{name(tofu, key)}"
    found = {("s3:GetObject", f"{arn(key)}/*") for key in spec["read"]}
    found |= {("s3:ListBucket", arn(key)) for key in spec["read"]}
    found |= {("s3:PutObject", f"{arn(key)}/*") for key in spec["write"]}
    return found


def test_fmt_and_validate(lab):
    tofu, _ = lab
    fmt = tofu.run("fmt", "-check", "-recursive", "-diff", check=False)
    assert fmt.returncode == 0, f"tofu fmt -check -recursive báo tệp chưa định dạng:\n{tail(fmt)}"
    validate = tofu.run("validate", "-no-color", check=False)
    assert validate.returncode == 0, f"tofu validate lỗi:\n{tail(validate)}"


def test_buckets_named_by_environment(applied):
    s3 = localstack_client("s3")
    found = sorted(b["Name"] for b in s3.list_buckets()["Buckets"] if b["Name"].startswith(applied.prefix))
    assert found == sorted(name(applied, key) for key in VARS["buckets"]), f"Bucket trên LocalStack: {found}"


def test_versioning_follows_input(applied):
    s3 = localstack_client("s3")
    status = {key: s3.get_bucket_versioning(Bucket=name(applied, key)).get("Status") for key in VARS["buckets"]}
    assert status == {"media": "Enabled", "exports": None, "invoices": "Enabled"}, f"Versioning theo bucket: {status}"


def test_public_access_blocked(applied):
    s3 = localstack_client("s3")
    for key in VARS["buckets"]:
        config = s3.get_public_access_block(Bucket=name(applied, key))["PublicAccessBlockConfiguration"]
        assert all(config.values()) and len(config) == 4, f"Bucket {key} chưa chặn đủ 4 cờ public access: {config}"


def test_tags(applied):
    s3 = localstack_client("s3")
    for key in VARS["buckets"]:
        tags = {t["Key"]: t["Value"] for t in s3.get_bucket_tagging(Bucket=name(applied, key))["TagSet"]}
        assert TAGS.items() <= tags.items(), f"Bucket {key} thiếu tag chung {TAGS}, đang có {tags}"


@pytest.mark.parametrize("service", sorted(VARS["services"]))
def test_role_least_privilege(applied, service):
    iam = localstack_client("iam")
    role = name(applied, service)
    trust = iam.get_role(RoleName=role)["Role"]["AssumeRolePolicyDocument"]
    trust = json.loads(trust) if isinstance(trust, str) else trust
    principals = json.dumps([s.get("Principal") for s in trust.get("Statement", [])])
    assert "ecs-tasks.amazonaws.com" in principals, f"Role {role} phải cho ecs-tasks.amazonaws.com assume: {trust}"
    found = role_grants(role)
    expected = expected_grants(applied, service)
    assert found == expected, (f"Quyền của {role} phải đúng bằng đầu vào (không thừa, không thiếu).\nThừa: {sorted(found - expected)}\n"
                               f"Thiếu: {sorted(expected - found)}")


def test_outputs(applied):
    outputs = applied.output()
    assert outputs.get("bucket_names") == {key: name(applied, key) for key in VARS["buckets"]}
    assert outputs.get("bucket_arns") == {key: f"arn:aws:s3:::{name(applied, key)}" for key in VARS["buckets"]}
    assert outputs.get("role_names") == {key: name(applied, key) for key in VARS["services"]}


def test_second_plan_has_no_changes(applied):
    assert applied.output().get("bucket_names"), "Chưa có bucket nào được tạo"
    result = applied.plan("-no-color", "-detailed-exitcode", check=False)
    assert result.returncode == 0, f"Plan lần hai phải 'No changes' (mã 0), nhận mã {result.returncode}:\n{tail(result)}"


def test_adding_bucket_only_adds(applied):
    extra = {**VARS, "buckets": {**VARS["buckets"], "reports": {}}}
    path = applied.write("zz-extra.auto.tfvars.json", json.dumps(extra))
    try:
        plan = applied.plan_json("-no-color")
    finally:
        path.unlink()
    changes = {r["address"]: r["change"]["actions"] for r in plan["resource_changes"] if r["change"]["actions"] not in (["no-op"], ["read"])}
    assert changes, "Thêm bucket reports mà plan không tạo gì"
    wrong = {addr: actions for addr, actions in changes.items() if actions != ["create"] or '"reports"' not in addr}
    assert not wrong, f"Thêm một khoá vào buckets chỉ được tạo tài nguyên của khoá đó, không đụng tài nguyên khác: {wrong}"


@pytest.mark.parametrize("case", sorted(BAD_INPUTS))
def test_validation_rejects_bad_input(applied, case):
    path = applied.write("zz-bad.auto.tfvars.json", json.dumps({**VARS, **BAD_INPUTS[case]}))
    try:
        result = applied.plan("-no-color", check=False)
    finally:
        path.unlink()
    assert result.returncode != 0, f"Đầu vào sai ({case}) mà plan vẫn chạy: thiếu validation"
    assert "Invalid value for variable" in f"{result.stdout}{result.stderr}", (
        f"Đầu vào sai ({case}) phải bị chặn bằng khối validation của biến (lỗi 'Invalid value for variable'):\n{tail(result)}")
