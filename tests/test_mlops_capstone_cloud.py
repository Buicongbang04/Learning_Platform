"""Bản tham chiếu `capstone/solutions/project/cloud/teardown.sh`: đường hỏi cloud (không có `--inventory`) với `aws` giả.

Test chấm của M11 chỉ chạy `teardown.sh` với `--inventory`; đường đọc output thật của `aws` (JSON nhiều dòng, phân trang,
vùng) chỉ kiểm được trên bản tham chiếu vì người học được chọn lệnh truy vấn riêng.
"""

import json
import os
import re
import sys
from pathlib import Path

import pytest

from testkit import run_sandboxed

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tracks" / "mlops" / "capstone" / "solutions" / "project" / "cloud" / "teardown.sh"
ACCOUNT = "111122223333"
TAGGED = [
    {"ResourceARN": "arn:aws:s3:::eta-mlops-models-7f3a",
     "Tags": [{"Key": "project", "Value": "eta-mlops"}, {"Key": "milestone", "Value": "m11"}]},
    {"ResourceARN": "arn:aws:lambda:{region}:111122223333:function:eta-mlops-health",
     "Tags": [{"Key": "project", "Value": "eta-mlops"}]},
    {"ResourceARN": "arn:aws:logs:{region}:111122223333:log-group:/aws/lambda/eta-mlops-health",
     "Tags": [{"Key": "project", "Value": "eta-mlops"}]},
]
ROLES = {
    "eta-mlops-health-role": [{"Key": "project", "Value": "eta-mlops"}, {"Key": "owner", "Value": "me"}],
    "eta-mlops-scratch-role": [{"Key": "project", "Value": "eta-mlops-staging"}],
}
BUDGETS = {
    "eta-mlops-monthly": [{"Key": "project", "Value": "eta-mlops"}],
    "eta-mlops-staging": [{"Key": "project", "Value": "eta-mlops-staging"}],
    "account-wide": [],
}
READ_ONLY = re.compile(r"^(get|list|describe)-")
FAKE_AWS = r'''
import json, os, sys

args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps(args) + "\n")
data = json.load(open(os.environ["FAKE_DATA"]))


def opt(name):
    return args[args.index(name) + 1] if name in args else None


if args[:2] == ["resourcegroupstaggingapi", "get-resources"]:
    if "--pagination-token" in args:
        sys.exit("fake aws: CLI tự phân trang get-resources; token tay tắt việc đó và chỉ trả một trang")
    region = opt("--region") or "default-cli-region"
    found = [] if region != data["region"] else data["tagged"]
    out = {"ResourceTagMappingList": json.loads(json.dumps(found).replace("{region}", region))}
elif args[:2] == ["iam", "list-roles"]:
    out = {"Roles": [{"RoleName": n, "Arn": f"arn:aws:iam::{data['account']}:role/eta-mlops/{n}", "Path": "/eta-mlops/"}
                     for n in data["roles"]]}
elif args[:2] == ["iam", "list-role-tags"]:
    out = {"Tags": data["roles"][opt("--role-name")], "IsTruncated": False}
elif args[:2] == ["sts", "get-caller-identity"]:
    out = {"UserId": "AIDAEXAMPLE", "Account": data["account"], "Arn": f"arn:aws:iam::{data['account']}:user/me"}
elif args[:2] == ["budgets", "describe-budgets"]:
    assert opt("--account-id") == data["account"], args
    out = {"Budgets": [{"BudgetName": n, "BudgetType": "COST", "TimeUnit": "MONTHLY"} for n in data["budgets"]]}
elif args[:2] == ["budgets", "list-tags-for-resource"]:
    out = {"ResourceTags": data["budgets"][opt("--resource-arn").rsplit("/", 1)[-1]]}
elif args[:2] in (["lambda", "delete-function"], ["logs", "delete-log-group"]):
    sys.exit(0)
else:
    sys.exit(f"fake aws: lệnh lạ {args}")
print(json.dumps(out, indent=4))
'''


@pytest.fixture
def live(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "aws").write_text(f"#!{sys.executable}\n{FAKE_AWS}", encoding="utf-8")
    (fake / "aws").chmod(0o755)
    log = tmp_path / "aws.log"

    def run(*args, deployed="us-east-1", env=None):
        data = tmp_path / "data.json"
        data.write_text(json.dumps({"tagged": TAGGED, "roles": ROLES, "budgets": BUDGETS, "account": ACCOUNT,
                                    "region": deployed}), encoding="utf-8")
        log.unlink(missing_ok=True)
        full_env = {"PATH": f"{fake}:{os.path.dirname(sys.executable)}:/usr/bin:/bin", "FAKE_LOG": str(log),
                    "FAKE_DATA": str(data), **(env or {})}
        result = run_sandboxed(["bash", str(SCRIPT), *args], writable=[tmp_path], cwd=tmp_path, env=full_env, timeout=60)
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls

    return run


def would_delete(stdout: str) -> list[str]:
    return [line.split()[3] for line in stdout.splitlines() if line.startswith("WOULD DELETE")]


def assert_read_only(calls):
    writes = [c for c in calls if len(c) < 2 or not READ_ONLY.match(c[1])]
    assert not writes, f"dry-run hay lúc liệt kê chỉ được gọi lệnh đọc, đã gọi: {writes}"


def test_dry_run_reads_multiline_aws_json(live):
    result, calls = live("--dry-run")
    assert result.returncode == 0, result.stderr
    assert would_delete(result.stdout) == [
        "arn:aws:lambda:us-east-1:111122223333:function:eta-mlops-health",
        "arn:aws:logs:us-east-1:111122223333:log-group:/aws/lambda/eta-mlops-health",
        "arn:aws:s3:::eta-mlops-models-7f3a",
        "arn:aws:iam::111122223333:role/eta-mlops/eta-mlops-health-role",
        "arn:aws:budgets::111122223333:budget/eta-mlops-monthly",
    ]
    tagging = [c for c in calls if c[:2] == ["resourcegroupstaggingapi", "get-resources"]]
    assert len(tagging) == 1 and tagging[0][tagging[0].index("--region") + 1] == "us-east-1"
    assert_read_only(calls)
    assert "vùng us-east-1" in result.stderr


def test_region_flag_and_env_reach_the_tagging_api(live):
    result, _ = live("--dry-run", deployed="eu-west-1")
    assert would_delete(result.stdout) == [
        "arn:aws:iam::111122223333:role/eta-mlops/eta-mlops-health-role",
        "arn:aws:budgets::111122223333:budget/eta-mlops-monthly",
    ]
    for args, env in ((["--region", "eu-west-1"], None), ([], {"ETA_AWS_REGION": "eu-west-1"})):
        result, calls = live("--dry-run", *args, deployed="eu-west-1", env=env)
        assert result.returncode == 0, result.stderr
        assert len(would_delete(result.stdout)) == 5
        assert all(c[c.index("--region") + 1] == "eu-west-1" for c in calls if c[0] == "resourcegroupstaggingapi")
        assert_read_only(calls)


def test_aws_failure_while_listing_stops_before_any_delete(live, tmp_path):
    result, calls = live("--yes", env={"FAKE_DATA": str(tmp_path / "missing.json")})
    assert result.returncode != 0
    assert "DELETE" not in result.stdout
    assert calls and len(calls) == 1
    assert_read_only(calls)


def test_regional_deletes_use_the_region_in_the_arn(live, tmp_path):
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"resources": [
        {"id": "arn:aws:lambda:eu-west-1:111122223333:function:eta-mlops-health", "type": "aws_lambda_function",
         "name": "eta-mlops-health", "tags": {"project": "eta-mlops"}},
        {"id": "arn:aws:logs:ap-southeast-1:111122223333:log-group:/aws/lambda/eta-mlops-health",
         "type": "aws_cloudwatch_log_group", "name": "/aws/lambda/eta-mlops-health", "tags": {"project": "eta-mlops"}},
    ]}), encoding="utf-8")
    result, calls = live("--dry-run", "--inventory", str(inventory))
    assert result.returncode == 0 and not calls
    assert "vùng" not in result.stderr and "inventory" in result.stderr
    result, calls = live("--yes", "--inventory", str(inventory))
    assert result.returncode == 0, result.stderr
    regions = {c[1]: c[c.index("--region") + 1] for c in calls if "--region" in c}
    assert regions == {"delete-function": "eu-west-1", "delete-log-group": "ap-southeast-1"}, calls


GOOD_LAMBDA = {"id": "arn:aws:lambda:us-east-1:111122223333:function:eta-mlops-health", "type": "aws_lambda_function",
               "name": "eta-mlops-health", "tags": {"project": "eta-mlops"}}
BAD = [
    {"id": "arn:aws:s3:::--recursive", "type": "aws_s3_bucket", "name": "--recursive", "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:iam::111122223333:role/eta-mlops/x", "type": "aws_iam_role", "name": "-x",
     "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:lambda:us-east-1;id:111122223333:function:f2", "type": "aws_lambda_function", "name": "f2",
     "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:logs:--profile:111122223333:log-group:/aws/lambda/g", "type": "aws_cloudwatch_log_group",
     "name": "/aws/lambda/g", "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:budgets::--x:budget/eta-mlops-monthly", "type": "aws_budgets_budget", "name": "eta-mlops-monthly",
     "tags": {"project": "eta-mlops"}},
    {"id": "eta-mlops-monthly", "type": "aws_budgets_budget", "name": "eta-mlops-monthly", "tags": {"project": "eta-mlops"}},
]


@pytest.fixture
def unsafe_inventory(tmp_path):
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps({"resources": [GOOD_LAMBDA, *BAD]}), encoding="utf-8")
    return path


def test_unsafe_names_regions_and_accounts_are_skipped_with_a_warning(live, unsafe_inventory):
    result, calls = live("--dry-run", "--inventory", str(unsafe_inventory))
    assert result.returncode == 0 and not calls
    assert would_delete(result.stdout) == [GOOD_LAMBDA["id"]]
    assert result.stderr.count("WARN: bỏ qua") == len(BAD)
    result, calls = live("--yes", "--inventory", str(unsafe_inventory))
    assert result.returncode != 0, "tài nguyên bị bỏ qua vẫn còn đó, --yes phải exit khác 0"
    assert calls == [["lambda", "delete-function", "--region", "us-east-1", "--function-name", "eta-mlops-health"]]


def test_invalid_region_flag_is_refused_before_any_call(live):
    result, calls = live("--dry-run", "--region", "us-east-1 --profile x")
    assert result.returncode != 0 and not calls
