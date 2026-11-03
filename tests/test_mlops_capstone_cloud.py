"""Bản tham chiếu `capstone/solutions/project/cloud/teardown.sh`: đường hỏi cloud (không có `--inventory`) với `aws` giả.

Test chấm của M11 chỉ chạy `teardown.sh` với `--inventory`; đường đọc output thật của `aws` (JSON nhiều dòng, phân trang,
vùng) chỉ kiểm được trên bản tham chiếu vì người học được chọn lệnh truy vấn riêng.
"""

import json
import os
import sys
from pathlib import Path

import pytest

from testkit import run_sandboxed

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tracks" / "mlops" / "capstone" / "solutions" / "project" / "cloud" / "teardown.sh"
ACCOUNT = "111122223333"
PAGES = [
    {"ResourceTagMappingList": [
        {"ResourceARN": "arn:aws:s3:::eta-mlops-models-7f3a",
         "Tags": [{"Key": "project", "Value": "eta-mlops"}, {"Key": "milestone", "Value": "m11"}]},
        {"ResourceARN": "arn:aws:lambda:{region}:111122223333:function:eta-mlops-health",
         "Tags": [{"Key": "project", "Value": "eta-mlops"}]},
    ], "PaginationToken": "page-2"},
    {"ResourceTagMappingList": [
        {"ResourceARN": "arn:aws:logs:{region}:111122223333:log-group:/aws/lambda/eta-mlops-health",
         "Tags": [{"Key": "project", "Value": "eta-mlops"}]},
        {"ResourceARN": "arn:aws:budgets::111122223333:budget/eta-mlops-monthly",
         "Tags": [{"Key": "project", "Value": "eta-mlops"}]},
    ], "PaginationToken": ""},
]
ROLES = {
    "eta-mlops-health-role": [{"Key": "project", "Value": "eta-mlops"}, {"Key": "owner", "Value": "me"}],
    "eta-mlops-scratch-role": [{"Key": "project", "Value": "eta-mlops-staging"}],
}
FAKE_AWS = r'''
import json, os, sys

args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps(args) + "\n")
data = json.load(open(os.environ["FAKE_DATA"]))


def opt(name):
    return args[args.index(name) + 1] if name in args else None


if args[:2] == ["resourcegroupstaggingapi", "get-resources"]:
    region = opt("--region") or "default-cli-region"
    page = data["pages"][1 if opt("--pagination-token") == "page-2" else 0]
    out = json.loads(json.dumps(page).replace("{region}", region))
    if region != data["region"]:
        out = {"ResourceTagMappingList": [], "PaginationToken": ""}
elif args[:2] == ["iam", "list-roles"]:
    out = {"Roles": [{"RoleName": n, "Arn": f"arn:aws:iam::{data['account']}:role/eta-mlops/{n}", "Path": "/eta-mlops/"}
                     for n in data["roles"]]}
elif args[:2] == ["iam", "list-role-tags"]:
    out = {"Tags": data["roles"][opt("--role-name")], "IsTruncated": False}
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
        data.write_text(json.dumps({"pages": PAGES, "roles": ROLES, "account": ACCOUNT, "region": deployed}), encoding="utf-8")
        log.unlink(missing_ok=True)
        full_env = {"PATH": f"{fake}:{os.path.dirname(sys.executable)}:/usr/bin:/bin", "FAKE_LOG": str(log),
                    "FAKE_DATA": str(data), **(env or {})}
        result = run_sandboxed(["bash", str(SCRIPT), *args], writable=[tmp_path], cwd=tmp_path, env=full_env, timeout=60)
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls

    return run


def would_delete(stdout: str) -> list[str]:
    return [line.split()[3] for line in stdout.splitlines() if line.startswith("WOULD DELETE")]


def test_dry_run_reads_multiline_aws_json_and_pages(live):
    result, calls = live("--dry-run")
    assert result.returncode == 0, result.stderr
    ids = would_delete(result.stdout)
    assert ids == [
        "arn:aws:lambda:us-east-1:111122223333:function:eta-mlops-health",
        "arn:aws:logs:us-east-1:111122223333:log-group:/aws/lambda/eta-mlops-health",
        "arn:aws:s3:::eta-mlops-models-7f3a",
        "arn:aws:iam::111122223333:role/eta-mlops/eta-mlops-health-role",
        "arn:aws:budgets::111122223333:budget/eta-mlops-monthly",
    ]
    tagging = [c for c in calls if c[:2] == ["resourcegroupstaggingapi", "get-resources"]]
    assert len(tagging) == 2 and all(c[c.index("--region") + 1] == "us-east-1" for c in tagging)


def test_region_flag_and_env_reach_the_tagging_api(live):
    result, _ = live("--dry-run", deployed="eu-west-1")
    assert would_delete(result.stdout) == ["arn:aws:iam::111122223333:role/eta-mlops/eta-mlops-health-role"]
    for args, env in ((["--region", "eu-west-1"], None), ([], {"ETA_AWS_REGION": "eu-west-1"})):
        result, calls = live("--dry-run", *args, deployed="eu-west-1", env=env)
        assert result.returncode == 0, result.stderr
        assert len(would_delete(result.stdout)) == 5
        assert all(c[c.index("--region") + 1] == "eu-west-1" for c in calls if c[0] == "resourcegroupstaggingapi")


def test_aws_failure_while_listing_stops_before_any_delete(live, tmp_path):
    result, calls = live("--yes", env={"FAKE_DATA": str(tmp_path / "missing.json")})
    assert result.returncode != 0
    assert "DELETE" not in result.stdout
