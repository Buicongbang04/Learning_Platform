import re
import shutil
import subprocess

import pytest

from testkit import Exercise

ex = Exercise(__file__)


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(re.split(r"\s(#|//)|^(#|//)", line)[0] for line in text.splitlines())


def tf():
    return strip_comments(ex.read("main.tf"))


def blocks(text, header_regex):
    """Nội dung các khối có header khớp regex (đếm ngoặc nhọn)."""
    result = []
    for match in re.finditer(header_regex + r"\s*\{", text):
        depth, i = 1, match.end()
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        result.append(text[match.end(): i - 1])
    return result


def resources(text, rtype):
    return blocks(text, rf'resource\s+"{rtype}"\s+"\w+"')


def data_blocks(text, dtype):
    return blocks(text, rf'data\s+"{dtype}"\s+"\w+"')


def test_terraform_block_and_variables():
    text = tf()
    terraform = blocks(text, r"terraform")
    assert terraform, "Thiếu khối terraform {}"
    assert "required_version" in terraform[0]
    assert re.search(r'source\s*=\s*"hashicorp/aws"', terraform[0])
    assert re.search(r"aws\s*=\s*\{[^}]*version\s*=", terraform[0], re.S), "Provider aws cần version"
    assert blocks(text, r'variable\s+"environment"'), 'Thiếu variable "environment"'
    region = blocks(text, r'variable\s+"region"')
    assert region and "default" in region[0]


def test_bucket_and_public_access_block():
    text = tf()
    buckets = resources(text, "aws_s3_bucket")
    assert buckets and any("var.environment" in b for b in buckets), "Tên bucket phải phụ thuộc var.environment"
    pabs = resources(text, "aws_s3_bucket_public_access_block")
    assert pabs, "Thiếu aws_s3_bucket_public_access_block"
    for flag in ("block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"):
        assert re.search(rf"{flag}\s*=\s*true", pabs[0]), f"{flag} phải = true"


def test_trust_policy_for_glue():
    text = tf()
    roles = resources(text, "aws_iam_role")
    assert roles, "Thiếu aws_iam_role"
    trust = "\n".join(roles) + "\n".join(data_blocks(text, "aws_iam_policy_document"))
    assert '"glue.amazonaws.com"' in trust, "Trust policy phải cho service glue.amazonaws.com"
    assert "sts:AssumeRole" in trust
    assert "assume_role_policy" in "\n".join(roles)
    assert not re.search(r'Principal\s*=\s*"\*"', text), "Không được Principal = \"*\""
    assert not re.search(r'AWS\s*=\s*"\*"', text), 'Không được Principal AWS = "*"'
    assert not re.search(r'identifiers\s*=\s*\[\s*"\*"\s*\]', text), "Không được identifiers [\"*\"]"


def permission_text(text):
    parts = resources(text, "aws_iam_policy") + resources(text, "aws_iam_role_policy")
    parts += data_blocks(text, "aws_iam_policy_document")
    return "\n".join(parts)


def test_least_privilege_permissions():
    text = tf()
    perms = permission_text(text)
    assert perms, "Thiếu aws_iam_policy / aws_iam_role_policy"
    for action in ("s3:GetObject", "s3:PutObject", "s3:ListBucket"):
        assert action in perms, f"Thiếu {action}"
    assert re.search(r"aws_s3_bucket\.\w+\.arn\}/raw/\*", perms), "GetObject phải trỏ ${aws_s3_bucket.X.arn}/raw/*"
    assert re.search(r"aws_s3_bucket\.\w+\.arn\}/curated/\*", perms), "PutObject phải trỏ .../curated/*"
    assert not re.search(r'"(\*|s3:\*)"', perms), 'Không dùng action/resource "*" hoặc "s3:*"'
    assert "arn:aws:s3:::" not in perms, "Không gõ cứng ARN bucket, hãy tham chiếu aws_s3_bucket.X.arn"


def test_policy_attached_to_role():
    text = tf()
    attachments = resources(text, "aws_iam_role_policy_attachment")
    inline = resources(text, "aws_iam_role_policy")
    custom_attached = any("aws_iam_policy." in a for a in attachments) or any("aws_iam_role." in i for i in inline)
    assert custom_attached, "Permission policy phải được gắn vào role"
    assert any("service-role/AWSGlueServiceRole" in a for a in attachments), "Thiếu attachment AWSGlueServiceRole"
    assert all("aws_iam_role." in a for a in attachments), "Attachment phải tham chiếu role"


def test_output_role_arn():
    outs = blocks(tf(), r'output\s+"\w+"')
    assert any(re.search(r"aws_iam_role\.\w+\.arn", o) for o in outs), "Cần output ARN của role"


def test_no_static_credentials():
    text = tf()
    assert not re.search(r"\b(access_key|secret_key)\s*=", text)
    assert not re.search(r'resource\s+"aws_iam_(access_key|user)"', text), "Dùng role, không tạo IAM user/access key"


def test_terraform_validate(tmp_path):
    binary = shutil.which("terraform") or shutil.which("tofu")
    if not binary:
        pytest.skip("Không có terraform/tofu, bỏ qua validate")
    shutil.copy(ex.path("main.tf"), tmp_path / "main.tf")
    init = subprocess.run([binary, "init", "-backend=false", "-input=false"], cwd=tmp_path,
                          capture_output=True, text=True, timeout=300)
    if init.returncode != 0:
        pytest.skip("terraform init thất bại (có thể do không có mạng): " + init.stderr[-300:])
    result = subprocess.run([binary, "validate", "-no-color"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
