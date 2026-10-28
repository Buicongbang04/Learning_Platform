"""Kiểm tra policy bằng một evaluator IAM thu nhỏ (không cần tài khoản AWS)."""

import json
import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)

BUCKET = "arn:aws:s3:::olist-lake"


# ---------- evaluator IAM thu nhỏ ----------

def as_list(value):
    return value if isinstance(value, list) else [value]


def wildcard(pattern: str, value: str, ignore_case=False) -> bool:
    # IAM chỉ có * và ?; [ ] không phải ký tự đặc biệt
    regex = "".join(".*" if c == "*" else "." if c == "?" else re.escape(c) for c in pattern)
    return re.fullmatch(regex, value, re.I if ignore_case else 0) is not None


def condition_ok(condition: dict, context: dict) -> bool:
    for operator, pairs in condition.items():
        for key, expected in pairs.items():
            expected = [str(v) for v in as_list(expected)]
            actual = context.get(key)
            if operator == "StringEquals":
                ok = actual is not None and str(actual) in expected
            elif operator == "StringNotEquals":
                ok = actual is None or str(actual) not in expected
            elif operator == "StringLike":
                ok = actual is not None and any(wildcard(p, str(actual)) for p in expected)
            elif operator == "Bool":
                ok = actual is not None and str(actual).lower() in [e.lower() for e in expected]
            else:
                raise AssertionError(f"Evaluator không hỗ trợ operator {operator}")
            if not ok:
                return False
    return True


def statement_matches(stmt, action, resource, context) -> bool:
    assert "NotAction" not in stmt and "NotResource" not in stmt, "Bài này không dùng NotAction/NotResource"
    if not any(wildcard(a, action, ignore_case=True) for a in as_list(stmt["Action"])):
        return False
    if not any(wildcard(r, resource) for r in as_list(stmt["Resource"])):
        return False
    return condition_ok(stmt.get("Condition", {}), context)


def evaluate(policy, action, resource, context=None) -> str:
    context = {"aws:SecureTransport": "true", **(context or {})}
    decision = "ImplicitDeny"
    for stmt in policy["Statement"]:
        if statement_matches(stmt, action, resource, context):
            if stmt["Effect"] == "Deny":
                return "ExplicitDeny"
            decision = "Allow"
    return decision


# ---------- test ----------

def policy():
    return json.loads(ex.read("policy.json"))


def test_evaluator_sanity():
    p = {"Statement": [{"Effect": "Allow", "Action": "s3:Get*", "Resource": f"{BUCKET}/*"}]}
    assert evaluate(p, "s3:GetObject", f"{BUCKET}/a") == "Allow"
    assert evaluate(p, "s3:PutObject", f"{BUCKET}/a") == "ImplicitDeny"


def test_structure():
    p = policy()
    assert p["Version"] == "2012-10-17"
    assert "_TODO" not in json.dumps(p), "Xoá các khoá _TODO khi đã làm xong"
    sids = [s.get("Sid") for s in p["Statement"]]
    assert all(sids) and len(sids) == len(set(sids)), "Mỗi statement cần Sid riêng"


def test_no_broad_allow():
    for stmt in policy()["Statement"]:
        if stmt["Effect"] != "Allow":
            continue
        for action in as_list(stmt["Action"]):
            assert action not in ("*", "s3:*"), f"Allow quá rộng: {action}"
        for resource in as_list(stmt["Resource"]):
            assert resource != "*", "Allow trên Resource * là quá rộng"
            assert not resource.startswith("arn:aws:s3:::*"), "Không mở cho mọi bucket"


KMS = {"s3:x-amz-server-side-encryption": "aws:kms"}

ALLOWED = [
    ("s3:GetObject", f"{BUCKET}/raw/orders/year=2018/part-0.parquet", {}),
    ("s3:PutObject", f"{BUCKET}/curated/orders/part-0.parquet", KMS),
    ("s3:ListBucket", BUCKET, {"s3:prefix": "raw/orders/"}),
    ("s3:ListBucket", BUCKET, {"s3:prefix": "curated/"}),
]

DENIED = [
    ("s3:DeleteObject", f"{BUCKET}/raw/orders/part-0.parquet", {}),
    ("s3:DeleteObject", f"{BUCKET}/curated/orders/part-0.parquet", {}),
    ("s3:PutObject", f"{BUCKET}/raw/orders/part-0.parquet", KMS),
    ("s3:PutObject", f"{BUCKET}/curated/orders/part-0.parquet", {}),
    ("s3:PutObject", f"{BUCKET}/curated/orders/part-0.parquet", {"s3:x-amz-server-side-encryption": "AES256"}),
    ("s3:GetObject", f"{BUCKET}/gold/kpi.parquet", {}),
    ("s3:GetObject", "arn:aws:s3:::other-team-bucket/raw/x.csv", {}),
    ("s3:GetObject", "arn:aws:s3:::olist-lake-backup/raw/x.csv", {}),
    ("s3:ListBucket", BUCKET, {"s3:prefix": "gold/"}),
    ("s3:ListBucket", BUCKET, {}),
    ("s3:ListBucket", "arn:aws:s3:::other-team-bucket", {"s3:prefix": "raw/"}),
    ("s3:PutBucketPolicy", BUCKET, {}),
    ("s3:DeleteBucket", BUCKET, {}),
    ("iam:CreateUser", "*", {}),
    ("iam:PassRole", "arn:aws:iam::123456789012:role/admin", {}),
]


@pytest.mark.parametrize("action, resource, context", ALLOWED)
def test_allowed(action, resource, context):
    assert evaluate(policy(), action, resource, context) == "Allow"


@pytest.mark.parametrize("action, resource, context", DENIED)
def test_denied(action, resource, context):
    assert evaluate(policy(), action, resource, context) != "Allow"


@pytest.mark.parametrize("action, resource, context", ALLOWED)
def test_insecure_transport_explicitly_denied(action, resource, context):
    ctx = {**context, "aws:SecureTransport": "false"}
    assert evaluate(policy(), action, resource, ctx) == "ExplicitDeny"
