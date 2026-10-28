import re
import shutil
import subprocess

import pytest

from testkit import Exercise

ex = Exercise(__file__)


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(re.split(r"\s(#|//)|^(#|//)", line)[0] for line in text.splitlines())


def tf(name):
    return strip_comments(ex.read(name))


def all_tf():
    return "\n".join(tf(n) for n in ("main.tf", "variables.tf", "outputs.tf"))


def blocks(text, header_regex):
    """Trả về nội dung các khối có header khớp regex (đếm ngoặc nhọn)."""
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


def test_terraform_block():
    terraform = blocks(all_tf(), r"terraform")
    assert terraform, "Thiếu khối terraform {}"
    body = terraform[0]
    assert "required_version" in body
    assert re.search(r'source\s*=\s*"hashicorp/aws"', body)
    assert re.search(r'aws\s*=\s*\{[^}]*version\s*=', body, re.S), "Provider aws cần ràng buộc version"


def test_environment_validation():
    env = blocks(all_tf(), r'variable\s+"environment"')
    assert env, 'Thiếu variable "environment"'
    validation = blocks(env[0], r"validation")
    assert validation, "environment cần khối validation"
    for value in ("dev", "staging", "prod"):
        assert f'"{value}"' in validation[0]
    region = blocks(all_tf(), r'variable\s+"region"')
    assert region and "default" in region[0], 'Cần variable "region" có default'


def test_tags_via_locals():
    text = all_tf()
    loc = blocks(text, r"locals")
    assert any(re.search(r"environment\s*=\s*var\.environment", b) for b in loc), "locals cần tag environment"
    buckets = resources(text, "aws_s3_bucket")
    uses_local = buckets and all("local." in b and "tags" in b for b in buckets)
    default_tags = any(blocks(p, r"default_tags") for p in blocks(text, r'provider\s+"aws"'))
    assert uses_local or default_tags, "Bucket phải dùng tags từ locals (hoặc default_tags)"


def test_two_zone_buckets_per_environment():
    text = all_tf()
    buckets = resources(text, "aws_s3_bucket")
    assert buckets, "Thiếu aws_s3_bucket"
    joined = "\n".join(buckets) + text
    assert "raw" in joined and "curated" in joined, "Cần bucket raw và curated"
    for b in buckets:
        assert "var.environment" in b or "local." in b, "Tên bucket phải phụ thuộc môi trường"
    multi = len(buckets) >= 2 or any("for_each" in b or "count" in b for b in buckets)
    assert multi, "Cần ít nhất 2 bucket (hoặc for_each/count)"


def test_versioning_encryption_lifecycle():
    text = all_tf()
    versioning = resources(text, "aws_s3_bucket_versioning")
    assert versioning and all(re.search(r'status\s*=\s*"Enabled"', v) for v in versioning)
    sse = resources(text, "aws_s3_bucket_server_side_encryption_configuration")
    assert sse and all(re.search(r'sse_algorithm\s*=\s*"(AES256|aws:kms|aws:kms:dsse)"', s) for s in sse)
    lifecycle = resources(text, "aws_s3_bucket_lifecycle_configuration")
    assert lifecycle and all(re.search(r"\b(transition|expiration|noncurrent_version_expiration)\b", lc)
                             for lc in lifecycle)


def test_public_access_block():
    pabs = resources(all_tf(), "aws_s3_bucket_public_access_block")
    assert pabs, "Thiếu aws_s3_bucket_public_access_block"
    for p in pabs:
        for flag in ("block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"):
            assert re.search(rf"{flag}\s*=\s*true", p), f"{flag} phải = true"


def test_outputs():
    outs = blocks(tf("outputs.tf"), r'output\s+"\w+"')
    referencing = [o for o in outs if "aws_s3_bucket" in o]
    assert len(referencing) >= 2 or any("for" in o and "aws_s3_bucket" in o for o in outs), \
        "Cần output cho cả hai bucket"


def test_no_static_credentials():
    assert not re.search(r"\b(access_key|secret_key)\s*=", all_tf())


def test_terraform_validate(tmp_path):
    binary = shutil.which("terraform") or shutil.which("tofu")
    if not binary:
        pytest.skip("Không có terraform/tofu, bỏ qua validate")
    for name in ("main.tf", "variables.tf", "outputs.tf"):
        shutil.copy(ex.path(name), tmp_path / name)
    init = subprocess.run([binary, "init", "-backend=false", "-input=false"], cwd=tmp_path,
                          capture_output=True, text=True, timeout=300)
    if init.returncode != 0:
        pytest.skip("terraform init thất bại (có thể do không có mạng): " + init.stderr[-300:])
    result = subprocess.run([binary, "validate", "-no-color"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
