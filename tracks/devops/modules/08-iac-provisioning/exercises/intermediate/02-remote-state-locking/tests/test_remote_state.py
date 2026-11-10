import json
import zipfile
from pathlib import Path

import pytest

from testkit import Exercise, TofuLab, localstack_client

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
PASSPHRASE = "olist-state-passphrase-2026-11"
KEY = "olist/staging/platform.tfstate"
LOCK = {"ID": "5f1c2a9e-0d7b-4c3e-9a51-devopsex0001", "Operation": "OperationTypeApply", "Who": "ci@runner-17",
        "Version": "1.13.2", "Created": "2026-10-30T02:11:00Z", "Path": KEY, "Info": ""}
EXPECTED_STATE = {"aws_dynamodb_table.carts", "aws_ssm_parameter.carts_table"}


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


def text(result) -> str:
    return f"{result.stdout}\n{result.stderr}"


def encrypted(raw: str) -> bool:
    try:
        data = json.loads(raw)
    except ValueError:
        return False
    return "encrypted_data" in data and "resources" not in data


@pytest.fixture(scope="module")
def story():
    infra = ex.path("infra")
    with TofuLab(infra) as tofu:
        steps = {"lab": tofu, "bucket": f"{tofu.prefix}-tfstate"}
        tofu.env["TF_VAR_state_passphrase"] = PASSPHRASE
        backend = tofu.workdir / "backend.tf"
        if not backend.is_file():
            steps["error"] = "Thiếu infra/backend.tf"
            yield steps
            return
        backend_text = backend.read_text(encoding="utf-8")
        backend.unlink()
        s3 = localstack_client("s3")
        s3.create_bucket(Bucket=steps["bucket"])
        s3.put_bucket_versioning(Bucket=steps["bucket"], VersioningConfiguration={"Status": "Enabled"})
        try:
            init = tofu.init("-no-color", check=False)
            steps["local_apply"] = tofu.apply("-no-color", check=False) if init.returncode == 0 else init
            if steps["local_apply"].returncode != 0:
                steps["error"] = f"init/apply với state local lỗi:\n{tail(steps['local_apply'])}"
                yield steps
                return
            local = tofu.workdir / "terraform.tfstate"
            steps["local_state"] = local.read_text(encoding="utf-8") if local.is_file() else ""
            tofu.write("backend.tf", backend_text)
            steps["migrate"] = tofu.init("-no-color", "-migrate-state", "-force-copy", check=False)
            if steps["migrate"].returncode != 0:
                steps["error"] = f"tofu init -migrate-state lỗi:\n{tail(steps['migrate'])}"
                yield steps
                return
            steps["after_migrate"] = tofu.plan("-no-color", "-detailed-exitcode", check=False)
            steps["state"] = set(tofu.state("list", check=False).stdout.split())
        except pytest.fail.Exception as error:
            steps["error"] = str(error)
        yield steps


def need(story, key):
    if key not in story:
        pytest.fail(story.get("error", f"Chưa tới bước {key}"))
    return story[key]


def remote_state(story) -> str | None:
    s3 = localstack_client("s3")
    try:
        return s3.get_object(Bucket=story["bucket"], Key=KEY)["Body"].read().decode()
    except s3.exceptions.NoSuchKey:
        return None


def test_local_state_already_encrypted(story):
    raw = need(story, "local_state")
    assert raw, "Không thấy terraform.tfstate sau apply với backend local"
    assert encrypted(raw), "State local phải được mã hoá bằng khối encryption (có encrypted_data, không có resources rõ)"
    assert "carts" not in raw, "Tên tài nguyên đọc được trong state local: state chưa được mã hoá"


def test_state_migrated_to_s3_key(story):
    need(story, "migrate")
    raw = remote_state(story)
    assert raw is not None, f"Không thấy state ở s3://{story['bucket']}/{KEY}"
    assert encrypted(raw) and "carts" not in raw, "State trên S3 phải được mã hoá"


def test_state_usable_after_migration(story):
    result = need(story, "after_migrate")
    assert result.returncode == 0, f"Sau khi chuyển state, plan phải 'No changes' (mã 0):\n{tail(result)}"
    assert story["state"] == EXPECTED_STATE, f"State sau khi chuyển: {sorted(story['state'])}"


def plant_lock(bucket: str) -> None:
    localstack_client("s3").put_object(Bucket=bucket, Key=f"{KEY}.tflock", Body=json.dumps(LOCK).encode(),
                                       ContentType="application/json")


def lock_exists(bucket: str) -> bool:
    found = localstack_client("s3").list_objects_v2(Bucket=bucket, Prefix=f"{KEY}.tflock").get("Contents", [])
    return any(o["Key"] == f"{KEY}.tflock" for o in found)


def saved_plan(tofu, name: str) -> Path:
    result = tofu.run("plan", "-input=false", "-no-color", "-lock=false", f"-out={name}", check=False)
    assert result.returncode == 0, f"tofu plan -out lỗi:\n{tail(result)}"
    return tofu.workdir / name


def test_lock_blocks_second_writer_then_force_unlock(story):
    need(story, "after_migrate")
    tofu = story["lab"]
    s3 = localstack_client("s3")
    plant_lock(story["bucket"])
    try:
        blocked = tofu.plan("-no-color", "-lock-timeout=0s", check=False)
        unlock = tofu.run("force-unlock", "-force", LOCK["ID"], check=False)
        lock_left = lock_exists(story["bucket"])
    finally:
        s3.delete_object(Bucket=story["bucket"], Key=f"{KEY}.tflock")
    assert blocked.returncode != 0 and "Error acquiring the state lock" in text(blocked), (
        f"Có tệp khoá {KEY}.tflock của job khác mà plan vẫn chạy: backend chưa bật use_lockfile:\n{tail(blocked)}")
    assert "ci@runner-17" in text(blocked), "Thông báo khoá phải cho biết ai đang giữ khoá"
    assert unlock.returncode == 0, f"tofu force-unlock lỗi:\n{tail(unlock)}"
    assert not lock_left, f"Sau force-unlock tệp {KEY}.tflock vẫn còn trên bucket"
    again = tofu.plan("-no-color", "-lock-timeout=0s", check=False)
    assert again.returncode == 0, f"Sau force-unlock plan phải chạy được:\n{tail(again)}"


def test_wrong_passphrase_cannot_read_state(story):
    need(story, "after_migrate")
    tofu = story["lab"]
    tofu.env["TF_VAR_state_passphrase"] = "mat-khau-sai-0000000000"
    try:
        result = tofu.plan("-no-color", "-lock=false", check=False)
    finally:
        tofu.env["TF_VAR_state_passphrase"] = PASSPHRASE
    assert result.returncode != 0, "Passphrase sai mà vẫn đọc được state: state chưa thật sự được mã hoá"


def test_plan_file_encrypted(story):
    need(story, "after_migrate")
    tofu = story["lab"]
    path = saved_plan(tofu, "ci.tfplan")
    try:
        assert not zipfile.is_zipfile(path), "Tệp plan vẫn là zip đọc được: khối encryption chưa có phần plan"
        readable = tofu.run("show", "-no-color", "ci.tfplan", check=False)
        assert readable.returncode == 0, f"Có passphrase đúng mà tofu show không đọc được plan:\n{tail(readable)}"
        tofu.env["TF_VAR_state_passphrase"] = "mat-khau-sai-0000000000"
        try:
            locked = tofu.run("show", "-no-color", "ci.tfplan", check=False)
        finally:
            tofu.env["TF_VAR_state_passphrase"] = PASSPHRASE
        assert locked.returncode != 0, "Passphrase sai mà tofu show vẫn đọc được tệp plan"
    finally:
        path.unlink(missing_ok=True)


def test_checks_catch_backend_without_lockfile_or_encryption():
    with TofuLab(FIXTURES / "no-lockfile") as tofu:
        bucket = f"{tofu.prefix}-tfstate"
        localstack_client("s3").create_bucket(Bucket=bucket)
        tofu.init()
        tofu.apply()
        raw = localstack_client("s3").get_object(Bucket=bucket, Key=KEY)["Body"].read().decode()
        assert not encrypted(raw), "Backend không có khối encryption phải để state đọc được"
        plant_lock(bucket)
        result = tofu.plan("-no-color", "-lock-timeout=0s", check=False)
        assert result.returncode == 0 and "Error acquiring the state lock" not in text(result), (
            "Backend không bật use_lockfile thì tệp .tflock không chặn được ai: phép kiểm khoá phải dựa vào use_lockfile")
        localstack_client("s3").delete_object(Bucket=bucket, Key=f"{KEY}.tflock")
        assert zipfile.is_zipfile(saved_plan(tofu, "plain.tfplan")), "Không có encryption thì tệp plan phải là zip đọc được"
