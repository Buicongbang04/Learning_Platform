import json
import re
import shutil
from pathlib import Path

import pytest

from testkit import Exercise, TofuLab, localstack_client, run_sandboxed

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TRIVY_MIN = "0.76"
TEST_FILE = "tests/artifact_bucket.tftest.hcl"
MUTANTS = {
    "versioning-suspended": ('versioning_configuration {\n    status = "Enabled"', 'versioning_configuration {\n    status = "Suspended"'),
    "sse-aes256": ('      sse_algorithm     = "aws:kms"\n      kms_master_key_id = aws_kms_key.this.arn\n',
                   '      sse_algorithm = "AES256"\n'),
    "validation-removed": ('\n  validation {\n    condition     = var.noncurrent_days >= 1 && var.noncurrent_days <= 365\n'
                           '    error_message = "noncurrent_days phải trong khoảng 1-365."\n  }\n', "\n"),
    "public-bucket-allowed": ("restrict_public_buckets = true", "restrict_public_buckets = false"),
    "rotation-off": ("enable_key_rotation     = true", "enable_key_rotation     = false"),
}
IGNORE_COMMENT = re.compile(r"(trivy|tfsec):ignore", re.I)


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


def run_module_tests(module: Path, tests: Path, mutate: tuple[str, str] | None = None):
    with TofuLab(module) as tofu:
        if mutate:
            for name in ("main.tf", "variables.tf"):
                path = tofu.workdir / name
                text = path.read_text(encoding="utf-8")
                if mutate[0] in text:
                    path.write_text(text.replace(mutate[0], mutate[1]), encoding="utf-8")
                    break
            else:
                pytest.fail(f"Đột biến không áp được vào module tham chiếu: {mutate[0]!r}")
        shutil.rmtree(tofu.workdir / "tests", ignore_errors=True)
        tofu.write(TEST_FILE, tests.read_text(encoding="utf-8"))
        tofu.write("ci.auto.tfvars.json", json.dumps({"name": "reports"}))
        tofu.init("-no-color")
        return tofu.run("test", "-no-color", check=False)


def passed_runs(result) -> int:
    match = re.search(r"(\d+) passed, (\d+) failed", result.stdout)
    return int(match.group(1)) if match else 0


def trivy_findings(modules: Path, tmp_path: Path) -> list[str]:
    ex.require_tool("trivy", TRIVY_MIN)
    work = tmp_path / "scan"
    shutil.copytree(modules, work, ignore=shutil.ignore_patterns(".terraform", "tests"))
    (tmp_path / "empty.yaml").write_text("", encoding="utf-8")
    (tmp_path / "trivyignore").write_text("", encoding="utf-8")
    cache = tmp_path / "cache"
    args = ["trivy", "config", "--config", str(tmp_path / "empty.yaml"), "--ignorefile", str(tmp_path / "trivyignore"),
            "--skip-check-update", "--disable-telemetry", "--skip-version-check", "--cache-dir", str(cache),
            "--severity", "HIGH,CRITICAL", "--format", "json", "--quiet", "--exit-code", "0", str(work)]
    result = run_sandboxed(args, writable=[tmp_path], cwd=tmp_path, env={}, timeout=300)
    assert result.returncode == 0, f"trivy config lỗi:\n{tail(result)}"
    data = json.loads(result.stdout)
    return [f"{r['Target']}: {m['ID']} {m['Severity']} {m['Title']}" for r in data.get("Results") or [] for m in r.get("Misconfigurations") or []]


@pytest.fixture(scope="module")
def learner_tests():
    return ex.path(f"modules/artifact-bucket/{TEST_FILE}")


def test_tests_pass_on_given_module(learner_tests):
    result = run_module_tests(ex.path("modules/artifact-bucket"), learner_tests)
    assert result.returncode == 0, f"tofu test của bạn phải pass trên module artifact-bucket:\n{tail(result)}"
    assert passed_runs(result) >= 4, f"Cần ít nhất 4 khối run, đang có {passed_runs(result)} run pass"


def test_tests_pass_on_reference(learner_tests):
    result = run_module_tests(FIXTURES / "reference", learner_tests)
    assert result.returncode == 0, (
        f"tofu test phải pass trên bản gốc của module (tests/fixtures/reference); đừng dựa vào chỗ bạn tự sửa trong module:\n{tail(result)}")


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_tests_catch_mutant(learner_tests, mutant):
    result = run_module_tests(FIXTURES / "reference", learner_tests, MUTANTS[mutant])
    assert result.returncode != 0, f"Module bị đột biến '{mutant}' mà tofu test của bạn vẫn pass: thiếu assert cho hành vi đó"


def test_mutants_change_reference():
    text = "".join((FIXTURES / "reference" / name).read_text(encoding="utf-8") for name in ("main.tf", "variables.tf"))
    missing = [name for name, (before, _) in MUTANTS.items() if before not in text]
    assert not missing, f"Đột biến không còn khớp module tham chiếu: {missing}"


def test_uses_mock_provider(learner_tests):
    text = learner_tests.read_text(encoding="utf-8")
    assert re.search(r'^\s*mock_provider\s+"aws"', text, re.M), "Test đơn vị phải dùng mock_provider \"aws\" để chạy không cần LocalStack"


def test_no_policy_suppression():
    found = [str(p.relative_to(ex.path("modules"))) for p in ex.path("modules").rglob("*.tf") if IGNORE_COMMENT.search(p.read_text(encoding="utf-8"))]
    assert not found, f"Không được tắt kiểm tra bằng chú thích trivy:ignore/tfsec:ignore: {found}"


def test_trivy_finds_no_high_or_critical(tmp_path):
    findings = trivy_findings(ex.path("modules"), tmp_path)
    assert not findings, "trivy config còn lỗi HIGH/CRITICAL:\n" + "\n".join(findings)


def test_trivy_check_catches_original_upload_bucket(tmp_path):
    original = FIXTURES / "original-upload-bucket"
    findings = trivy_findings(original, tmp_path)
    assert any("AWS-0086" in f for f in findings) and any("AWS-0132" in f for f in findings), findings


def test_modules_apply_on_localstack():
    with TofuLab(FIXTURES / "root") as tofu:
        for module in ("artifact-bucket", "upload-bucket"):
            source = ex.path(f"modules/{module}")
            for path in source.rglob("*.tf"):
                if "tests" not in path.relative_to(source).parts and ".terraform" not in path.parts:
                    tofu.write(f"modules/{module}/{path.relative_to(source).as_posix()}", path.read_text(encoding="utf-8"))
        tofu.init("-no-color")
        result = tofu.apply("-no-color", check=False)
        assert result.returncode == 0, f"Apply hai module trên LocalStack lỗi:\n{tail(result)}"
        outputs = tofu.output()
        s3 = localstack_client("s3")
        kms = localstack_client("kms")
        for key in ("reports_bucket", "uploads_bucket"):
            bucket = outputs[key]
            assert bucket in (f"{tofu.prefix}-reports", f"{tofu.prefix}-uploads"), f"Tên bucket sai: {bucket}"
            rule = s3.get_bucket_encryption(Bucket=bucket)["ServerSideEncryptionConfiguration"]["Rules"][0]
            assert rule["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "aws:kms", f"{bucket} chưa mã hoá bằng KMS"
            assert s3.get_bucket_versioning(Bucket=bucket).get("Status") == "Enabled", f"{bucket} chưa bật versioning"
            block = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
            assert all(block.values()), f"{bucket} chưa chặn public access"
        key = outputs["reports_key"]
        assert kms.get_key_rotation_status(KeyId=key)["KeyRotationEnabled"], "Khoá KMS của reports chưa bật xoay khoá"
