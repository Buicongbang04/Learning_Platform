import json
import shutil
from pathlib import Path

import pytest

from testkit import Exercise, TofuLab, localstack_client, run_sandboxed

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
NAMES = ("orders", "payments", "reviews")
EXPECTED_STATE = {f'aws_s3_bucket.exports["{n}"]' for n in NAMES} | {f'aws_s3_bucket_versioning.exports["{n}"]' for n in NAMES}
GUARD_CASES = {
    "safe-moves.json": ("", 0),
    "bucket-replaced.json": ("", 1),
    "table-replaced.json": ("", 1),
    "parameter-deleted.json": ("", 0),
    "payments-deleted.json": ("", 1),
    "payments-deleted.json+allow": ('aws_s3_bucket.exports["payments"]', 0),
    "table-replaced.json+allow-other": ('aws_s3_bucket.exports["payments"]', 1),
}


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


def actions(plan: dict) -> dict[str, list[str]]:
    return {r["address"]: r["change"]["actions"] for r in plan.get("resource_changes", [])}


def destructive(plan: dict) -> dict[str, list[str]]:
    return {a: acts for a, acts in actions(plan).items() if "delete" in acts or "create" in acts}


def swap_in(tofu, source: Path) -> None:
    for old in tofu.workdir.glob("*.tf"):
        old.unlink()
    for path in sorted(source.rglob("*")):
        if path.is_file() and ".terraform" not in path.parts and not path.name.endswith((".tfstate", ".tfstate.backup")):
            tofu.write(path.relative_to(source).as_posix(), path.read_text(encoding="utf-8"))


def seed(prefix: str) -> None:
    s3 = localstack_client("s3")
    for name in NAMES:
        s3.put_object(Bucket=f"{prefix}-exports-{name}", Key="2026-10/export.csv", Body=f"{name},1\n".encode())


def empty(prefix: str) -> None:
    s3 = localstack_client("s3")
    for name in NAMES:
        bucket = f"{prefix}-exports-{name}"
        try:
            versions = s3.list_object_versions(Bucket=bucket)
        except s3.exceptions.NoSuchBucket:
            continue
        objects = [{"Key": v["Key"], "VersionId": v["VersionId"]} for v in versions.get("Versions", []) + versions.get("DeleteMarkers", [])]
        if objects:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True})


def production(tofu) -> None:
    tofu.init()
    tofu.apply()
    seed(tofu.prefix)


def run_guard(guard: Path, plan: Path, tmp_path: Path, allow: str = ""):
    ex.require_tool("jq", "1.6")
    shutil.copyfile(guard, tmp_path / "plan-guard.sh")
    if plan.parent != tmp_path:
        shutil.copyfile(plan, tmp_path / plan.name)
    return run_sandboxed(["bash", "plan-guard.sh", plan.name], writable=[tmp_path], cwd=tmp_path, env={"ALLOW_DESTROY": allow},
                         timeout=60)


@pytest.fixture(scope="module")
def fixed():
    infra = ex.path("infra")
    with TofuLab(FIXTURES / "v1") as tofu:
        production(tofu)
        steps = {"lab": tofu}
        try:
            swap_in(tofu, infra)
            init = tofu.init("-no-color", check=False)
            if init.returncode != 0:
                steps["error"] = f"tofu init với cấu hình của bạn lỗi:\n{tail(init)}"
            else:
                steps["plan"] = tofu.plan_json("-no-color")
                if destructive(steps["plan"]):
                    steps["error"] = f"Plan vẫn tạo/xoá bucket nên test không apply: {destructive(steps['plan'])}"
                else:
                    steps["apply"] = tofu.apply("-no-color", check=False)
                    steps["after"] = tofu.plan("-no-color", "-detailed-exitcode", check=False)
                    steps["state"] = set(tofu.state("list").stdout.split())
                    path = tofu.write("zz-drop.auto.tfvars.json", json.dumps({"export_names": ["orders", "reviews"]}))
                    steps["drop"] = tofu.plan_json("-no-color")
                    path.unlink()
        except pytest.fail.Exception as error:
            steps["error"] = str(error)
        yield steps
        empty(tofu.prefix)


def need(steps, key):
    if key not in steps:
        pytest.fail(steps.get("error", f"Chưa tới bước {key}"))
    return steps[key]


def test_incident_config_reproduces_symptom():
    with TofuLab(FIXTURES / "v1") as tofu:
        production(tofu)
        swap_in(tofu, FIXTURES / "incident")
        tofu.init()
        plan = tofu.plan_json("-no-color")
        empty(tofu.prefix)
    found = destructive(plan)
    assert any(a.startswith("aws_s3_bucket.exports[") and acts == ["delete"] for a, acts in found.items()), found
    assert any(a.startswith('aws_s3_bucket.exports["') and acts == ["create"] for a, acts in found.items()), found


def test_fix_keeps_every_bucket(fixed):
    plan = need(fixed, "plan")
    assert not destructive(plan), f"Plan sau khi sửa không được tạo hay xoá gì: {destructive(plan)}"
    result = need(fixed, "apply")
    assert result.returncode == 0, f"Apply lỗi:\n{tail(result)}"
    s3 = localstack_client("s3")
    for name in NAMES:
        body = s3.get_object(Bucket=f"{fixed['lab'].prefix}-exports-{name}", Key="2026-10/export.csv")["Body"].read()
        assert body == f"{name},1\n".encode(), f"Dữ liệu trong bucket {name} đã mất"


def test_fix_keeps_for_each(fixed):
    state = need(fixed, "state")
    assert state == EXPECTED_STATE, f"State phải theo khoá tên (for_each), đang là {sorted(state)}"
    assert fixed["after"].returncode == 0, f"Plan sau apply phải 'No changes':\n{tail(fixed['after'])}"


def test_removing_one_name_touches_only_it(fixed):
    plan = {a: acts for a, acts in actions(need(fixed, "drop")).items() if acts not in (["no-op"], ["read"])}
    expected = {'aws_s3_bucket.exports["payments"]': ["delete"], 'aws_s3_bucket_versioning.exports["payments"]': ["delete"]}
    assert plan == expected, f"Bỏ payments khỏi danh sách chỉ được xoá đúng payments: {plan}"


@pytest.mark.parametrize("case", sorted(GUARD_CASES))
def test_plan_guard(tmp_path, case):
    allow, expected = GUARD_CASES[case]
    result = run_guard(ex.path("ci/plan-guard.sh"), FIXTURES / "plans" / case.split("+")[0], tmp_path, allow)
    assert result.returncode == expected, (
        f"plan-guard.sh với {case} (ALLOW_DESTROY={allow!r}) phải thoát {expected}, nhận {result.returncode}:\n{tail(result)}")
    if expected == 1:
        assert "aws_" in result.stdout + result.stderr, "Khi chặn, guard phải in địa chỉ tài nguyên bị xoá"


def test_plan_guard_on_real_plans(fixed, tmp_path):
    plan = tmp_path / "fixed.json"
    plan.write_text(json.dumps(need(fixed, "plan")), encoding="utf-8")
    result = run_guard(ex.path("ci/plan-guard.sh"), plan, tmp_path)
    assert result.returncode == 0, f"Guard chặn nhầm plan đã sửa:\n{tail(result)}"
    drop = tmp_path / "drop.json"
    drop.write_text(json.dumps(need(fixed, "drop")), encoding="utf-8")
    result = run_guard(ex.path("ci/plan-guard.sh"), drop, tmp_path)
    assert result.returncode == 1, "Guard phải chặn plan xoá bucket payments khi không có ALLOW_DESTROY"
