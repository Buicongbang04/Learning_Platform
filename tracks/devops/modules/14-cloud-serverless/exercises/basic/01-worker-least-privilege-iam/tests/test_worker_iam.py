import json
import re
from urllib.parse import unquote

import pytest

from testkit import Exercise, TofuLab, localstack_client

ex = Exercise(__file__)
REGION = "us-east-1"
TRUSTED = "ecs-tasks.amazonaws.com"


def as_list(value) -> list:
    if value is None:
        return []
    return [value] if isinstance(value, (str, dict)) else list(value)


def pattern(text: str, *, ignore_case: bool) -> re.Pattern:
    regex = "".join(".*" if c == "*" else "." if c == "?" else re.escape(c) for c in text)
    return re.compile(f"^{regex}$", re.I if ignore_case else 0)


def matches(patterns, value: str, *, ignore_case: bool) -> bool:
    return any(pattern(p, ignore_case=ignore_case).match(value) for p in as_list(patterns))


def applies(statement: dict, action: str, resource: str) -> bool:
    if "NotAction" in statement:
        action_ok = not matches(statement["NotAction"], action, ignore_case=True)
    else:
        action_ok = matches(statement.get("Action"), action, ignore_case=True)
    if "NotResource" in statement:
        resource_ok = not matches(statement["NotResource"], resource, ignore_case=False)
    else:
        resource_ok = matches(statement.get("Resource"), resource, ignore_case=False)
    return action_ok and resource_ok


def decide(policies: list[dict], action: str, resource: str) -> str:
    allowed = False
    for policy in policies:
        for statement in as_list(policy.get("Statement")):
            if not applies(statement, action, resource):
                continue
            if statement.get("Effect") == "Deny":
                return "explicitDeny"
            if statement.get("Effect") == "Allow":
                allowed = True
    return "allowed" if allowed else "implicitDeny"


def effective(identity: list[dict], boundary: dict | None, action: str, resource: str) -> str:
    first = decide(identity, action, resource)
    if first != "allowed" or boundary is None:
        return first
    return decide([boundary], action, resource)


def document(raw) -> dict:
    return raw if isinstance(raw, dict) else json.loads(unquote(raw))


def condition_problems(policies: list[dict], label: str) -> list[str]:
    found = []
    for policy in policies:
        for statement in as_list(policy.get("Statement")):
            if "Condition" in statement:
                found.append(f"{label}: statement {statement.get('Sid', '')!r} có Condition; parser của test không đánh giá "
                             "Condition, permission policy của bài này không cần nó")
            if statement.get("Effect") == "Allow" and ("NotAction" in statement or "NotResource" in statement):
                found.append(f"{label}: Allow kèm NotAction/NotResource cấp quyền cho mọi thứ còn lại, không phải least privilege")
    return found


@pytest.fixture(scope="module")
def lab():
    ex.require_localstack_devops("sqs", "secretsmanager")
    with TofuLab(ex.path("infra")) as tofu:
        result = tofu.init("-no-color", check=False)
        if result.returncode == 0:
            result = tofu.apply("-no-color", check=False)
        yield tofu, result


@pytest.fixture(scope="module")
def role(lab):
    tofu, result = lab
    output = "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])
    assert result.returncode == 0, f"init/apply lỗi:\n{output}"
    iam = localstack_client("iam")
    name = f"{tofu.prefix}-worker"
    data = iam.get_role(RoleName=name)["Role"]
    identity = [document(iam.get_role_policy(RoleName=name, PolicyName=policy)["PolicyDocument"])
                for policy in iam.list_role_policies(RoleName=name)["PolicyNames"]]
    for attached in iam.list_attached_role_policies(RoleName=name)["AttachedPolicies"]:
        meta = iam.get_policy(PolicyArn=attached["PolicyArn"])["Policy"]
        version = iam.get_policy_version(PolicyArn=attached["PolicyArn"], VersionId=meta["DefaultVersionId"])
        identity.append(document(version["PolicyVersion"]["Document"]))
    boundary_arn = (data.get("PermissionsBoundary") or {}).get("PermissionsBoundaryArn")
    boundary = None
    if boundary_arn:
        meta = iam.get_policy(PolicyArn=boundary_arn)["Policy"]
        version = iam.get_policy_version(PolicyArn=boundary_arn, VersionId=meta["DefaultVersionId"])
        boundary = document(version["PolicyVersion"]["Document"])
    secret = localstack_client("secretsmanager").describe_secret(SecretId=f"{tofu.prefix}/olist/db")["ARN"]
    account = localstack_client("sts").get_caller_identity()["Account"]
    return {"prefix": tofu.prefix, "trust": document(data["AssumeRolePolicyDocument"]), "identity": identity,
            "boundary_arn": boundary_arn, "boundary": boundary, "secret": secret, "account": account}


def arns(role: dict) -> dict[str, str]:
    p, account = role["prefix"], role["account"]
    return {
        "queue": f"arn:aws:sqs:{REGION}:{account}:{p}-jobs",
        "other_queue": f"arn:aws:sqs:{REGION}:{account}:{p}-jobs-archive",
        "report": f"arn:aws:s3:::{p}-reports/revenue/2026-11-11.csv",
        "export": f"arn:aws:s3:::{p}-reports/exports/customers.csv",
        "public_bucket": f"arn:aws:s3:::{p}-reports-public/revenue/2026-11-11.csv",
        "bucket": f"arn:aws:s3:::{p}-reports",
        "secret": role["secret"],
        "admin_secret": f"arn:aws:secretsmanager:{REGION}:{account}:secret:{p}/olist/admin-AbCdEf",
        "role_self": f"arn:aws:iam::{account}:role/{p}-worker",
        "role_admin": f"arn:aws:iam::{account}:role/{p}-admin",
        "kms_key": f"arn:aws:kms:{REGION}:{account}:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "kms_alias": f"arn:aws:kms:{REGION}:{account}:alias/{p}-reports",
        "prod_bucket": "arn:aws:s3:::olist-prod-data/orders.csv",
        "prod_queue": f"arn:aws:sqs:{REGION}:{account}:olist-prod-jobs",
        "prod_secret": f"arn:aws:secretsmanager:{REGION}:{account}:secret:olist-prod/db-AbCdEf",
    }


NEEDED = [
    ("sqs:ReceiveMessage", "queue"),
    ("sqs:DeleteMessage", "queue"),
    ("sqs:ChangeMessageVisibility", "queue"),
    ("sqs:GetQueueAttributes", "queue"),
    ("s3:PutObject", "report"),
    ("secretsmanager:GetSecretValue", "secret"),
]
FORBIDDEN = [
    ("sqs:SendMessage", "queue"),
    ("sqs:PurgeQueue", "queue"),
    ("sqs:DeleteQueue", "queue"),
    ("sqs:ReceiveMessage", "other_queue"),
    ("s3:GetObject", "report"),
    ("s3:DeleteObject", "report"),
    ("s3:PutObject", "export"),
    ("s3:PutObject", "public_bucket"),
    ("s3:PutBucketPolicy", "bucket"),
    ("secretsmanager:GetSecretValue", "admin_secret"),
    ("secretsmanager:PutSecretValue", "secret"),
    ("secretsmanager:DeleteSecret", "secret"),
    ("secretsmanager:ListSecrets", "*"),
    ("s3:PutObjectAcl", "report"),
    ("iam:PassRole", "role_admin"),
    ("iam:PassRole", "role_self"),
    ("iam:CreateRole", "role_admin"),
    ("iam:PutRolePolicy", "role_self"),
    ("sts:AssumeRole", "role_admin"),
    ("kms:Decrypt", "kms_key"),
    ("kms:Decrypt", "kms_alias"),
]
BOUNDARY_FORBIDDEN = [
    ("iam:CreateRole", "role_admin"),
    ("iam:PutRolePolicy", "role_self"),
    ("iam:AttachRolePolicy", "role_self"),
    ("iam:DeleteRolePermissionsBoundary", "role_self"),
    ("iam:PassRole", "role_admin"),
    ("sts:AssumeRole", "role_admin"),
    ("s3:PutObject", "prod_bucket"),
    ("sqs:ReceiveMessage", "prod_queue"),
    ("secretsmanager:GetSecretValue", "prod_secret"),
]


def test_policy_evaluator_self_check():
    policy = {"Statement": [
        {"Effect": "Allow", "Action": ["sqs:Receive*", "s3:PutObject"], "Resource": ["arn:aws:sqs:*:1:jobs", "arn:aws:s3:::b/r/*"]},
        {"Effect": "Deny", "Action": "s3:PutObject", "Resource": "arn:aws:s3:::b/r/private/*"},
        {"Effect": "Allow", "NotAction": "iam:*", "Resource": "arn:aws:dynamodb:*"},
    ]}
    assert decide([policy], "SQS:receivemessage", "arn:aws:sqs:us-east-1:1:jobs") == "allowed"
    assert decide([policy], "sqs:ReceiveMessage", "arn:aws:sqs:us-east-1:1:jobs-archive") == "implicitDeny"
    assert decide([policy], "s3:PutObject", "arn:aws:s3:::b/r/x.csv") == "allowed"
    assert decide([policy], "s3:PutObject", "arn:aws:s3:::b/r/private/x") == "explicitDeny"
    assert decide([policy], "dynamodb:Scan", "arn:aws:dynamodb:us-east-1:1:table/t") == "allowed"
    assert decide([policy], "iam:CreateRole", "arn:aws:dynamodb:x") == "implicitDeny"
    boundary = {"Statement": {"Effect": "Allow", "Action": "sqs:*", "Resource": "*"}}
    assert effective([policy], boundary, "s3:PutObject", "arn:aws:s3:::b/r/x.csv") == "implicitDeny"
    assert effective([policy], boundary, "sqs:ReceiveMessage", "arn:aws:sqs:us-east-1:1:jobs") == "allowed"


def test_trust_policy_only_ecs_tasks_from_this_account(role):
    statements = as_list(role["trust"].get("Statement"))
    assert len(statements) == 1, f"Trust policy cần đúng một statement, đang có {len(statements)}"
    statement = statements[0]
    assert statement.get("Effect") == "Allow" and as_list(statement.get("Action")) == ["sts:AssumeRole"], \
        "Trust policy chỉ cho sts:AssumeRole"
    principal = statement.get("Principal")
    assert isinstance(principal, dict) and set(principal) == {"Service"} and as_list(principal["Service"]) == [TRUSTED], \
        f"Principal phải đúng một service {TRUSTED}, đang là {principal}"
    condition = statement.get("Condition") or {}
    source_accounts = [as_list(values.get("aws:SourceAccount")) for test, values in condition.items()
                       if test in ("StringEquals", "StringLike") and isinstance(values, dict)]
    assert [role["account"]] in source_accounts, \
        "Trust policy cần Condition StringEquals aws:SourceAccount bằng ID tài khoản (chống confused deputy)"


def wildcard_problems(identity: list[dict]) -> list[str]:
    found = condition_problems(identity, "Permission policy")
    for policy in identity:
        for statement in as_list(policy.get("Statement")):
            if statement.get("Effect") != "Allow":
                continue
            for action in as_list(statement.get("Action")):
                if "*" in action or "?" in action:
                    found.append(f"Action {action!r} có wildcard; liệt kê từng action")
            if "*" in as_list(statement.get("Resource")):
                found.append(f"Statement {statement.get('Sid', '')!r} có Resource \"*\"")
    return found


def identity_problems(identity: list[dict], boundary: dict | None, targets: dict[str, str]) -> list[str]:
    found = []
    for action, target in NEEDED:
        got = effective(identity, boundary, action, targets[target])
        if got != "allowed":
            found.append(f"Worker cần {action} trên {targets[target]}, đang {got}")
    for action, target in FORBIDDEN:
        resource = targets.get(target, target)
        if effective(identity, boundary, action, resource) == "allowed":
            found.append(f"Worker không được {action} trên {resource}")
    return found


def boundary_problems(boundary: dict, targets: dict[str, str]) -> list[str]:
    found = condition_problems([boundary], "Boundary")
    for action, target in BOUNDARY_FORBIDDEN:
        if decide([boundary], action, targets[target]) == "allowed":
            found.append(f"Boundary vẫn cho {action} trên {targets[target]}")
    for action, target in NEEDED:
        if decide([boundary], action, targets[target]) != "allowed":
            found.append(f"Boundary chặn mất quyền worker cần: {action}")
    return found


def test_no_wildcard_grants(role):
    assert role["identity"], "Role chưa có permission policy nào"
    found = wildcard_problems(role["identity"])
    assert not found, "\n".join(found)


@pytest.mark.parametrize("action,target", NEEDED, ids=[f"{a}-{t}" for a, t in NEEDED])
def test_worker_can_do_its_job(role, action, target):
    resource = arns(role)[target]
    got = effective(role["identity"], role["boundary"], action, resource)
    assert got == "allowed", f"Worker cần {action} trên {resource}, đang {got}"


@pytest.mark.parametrize("action,target", FORBIDDEN, ids=[f"{a}-{t}" for a, t in FORBIDDEN])
def test_worker_cannot_do_more(role, action, target):
    resource = arns(role).get(target, target)
    got = effective(role["identity"], role["boundary"], action, resource)
    assert got != "allowed", f"Worker không được {action} trên {resource}"


def test_permissions_boundary_attached_and_scoped(role):
    expected = f"arn:aws:iam::{role['account']}:policy/{role['prefix']}-worker-boundary"
    assert role["boundary_arn"] == expected, f"Role cần permissions boundary {expected}, đang là {role['boundary_arn']}"
    found = boundary_problems(role["boundary"], arns(role))
    assert not found, "\n".join(found)


SAMPLE = {"prefix": "devops-ex-00000000", "account": "000000000000",
          "secret": "arn:aws:secretsmanager:us-east-1:000000000000:secret:devops-ex-00000000/olist/db-Q1w2E3"}
GOOD_IDENTITY = {"Statement": [
    {"Effect": "Allow", "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility", "sqs:GetQueueAttributes"],
     "Resource": "arn:aws:sqs:us-east-1:000000000000:devops-ex-00000000-jobs"},
    {"Effect": "Allow", "Action": "s3:PutObject", "Resource": "arn:aws:s3:::devops-ex-00000000-reports/revenue/*"},
    {"Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": SAMPLE["secret"]},
]}
GOOD_BOUNDARY = {"Statement": [
    {"Effect": "Allow", "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility", "sqs:GetQueueAttributes"],
     "Resource": "arn:aws:sqs:us-east-1:000000000000:devops-ex-00000000-*"},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"], "Resource": "arn:aws:s3:::devops-ex-00000000-*/*"},
    {"Effect": "Allow", "Action": "secretsmanager:GetSecretValue",
     "Resource": "arn:aws:secretsmanager:us-east-1:000000000000:secret:devops-ex-00000000/*"},
]}


def test_checks_pass_good_sample():
    targets = arns(SAMPLE)
    assert not wildcard_problems([GOOD_IDENTITY])
    assert not identity_problems([GOOD_IDENTITY], GOOD_BOUNDARY, targets)
    assert not boundary_problems(GOOD_BOUNDARY, targets)


@pytest.mark.parametrize("extra", [
    {"Effect": "Allow", "Action": "iam:PassRole", "Resource": "arn:aws:iam::000000000000:role/*"},
    {"Effect": "Allow", "Action": "kms:Decrypt", "Resource": "arn:aws:kms:us-east-1:000000000000:key/*"},
    {"Effect": "Allow", "Action": "sts:AssumeRole", "Resource": "arn:aws:iam::*:role/*"},
    {"Effect": "Allow", "Action": "s3:PutObjectAcl", "Resource": "arn:aws:s3:::devops-ex-00000000-reports/revenue/*"},
], ids=["passrole", "kms", "assume", "put-acl"])
def test_checks_catch_extra_identity_grant(extra):
    identity = {"Statement": [*GOOD_IDENTITY["Statement"], extra]}
    open_boundary = {"Statement": [*GOOD_BOUNDARY["Statement"], extra]}
    assert identity_problems([identity], open_boundary, arns(SAMPLE)), f"Bộ kiểm không bắt được {extra}"


def test_checks_catch_wildcard_action():
    identity = {"Statement": [{"Effect": "Allow", "Action": "s3:Put*", "Resource": "arn:aws:s3:::devops-ex-00000000-reports/revenue/*"}]}
    assert any("wildcard" in p for p in wildcard_problems([identity]))


@pytest.mark.parametrize("extra", [
    {"Effect": "Allow", "Action": "*", "Resource": "arn:aws:*:*:*:*"},
    {"Effect": "Allow", "Action": "iam:*", "Resource": "arn:aws:iam::000000000000:role/devops-ex-00000000-*"},
], ids=["all", "iam-prefix"])
def test_checks_catch_open_boundary(extra):
    boundary = {"Statement": [*GOOD_BOUNDARY["Statement"], extra]}
    assert boundary_problems(boundary, arns(SAMPLE)), f"Bộ kiểm không bắt được boundary {extra}"
