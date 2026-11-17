import json
from pathlib import Path

import pytest

from testkit import Exercise, TofuLab, localstack_client

ex = Exercise(__file__)
V1 = Path(__file__).parent / "fixtures" / "v1"
NAMES = ("invoices", "reports")
MOVES = {
    'module.documents.aws_s3_bucket.this["invoices"]': "aws_s3_bucket.invoices",
    'module.documents.aws_s3_bucket.this["reports"]': "aws_s3_bucket.reports",
    'module.documents.aws_s3_bucket_versioning.this["invoices"]': "aws_s3_bucket_versioning.invoices",
    'module.documents.aws_s3_bucket_versioning.this["reports"]': "aws_s3_bucket_versioning.reports",
}
IMPORTS = ("aws_s3_bucket.legacy_exports", "aws_s3_bucket_versioning.legacy_exports")
LEGACY_TAGS = {"Project": "olist-shop", "Owner": "data-team"}
FINOPS_TAG = {"Key": "cost-center", "Value": "fin-42"}
STATE = {*MOVES, *IMPORTS}


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


def changes(plan: dict) -> dict[str, dict]:
    return {r["address"]: r for r in plan.get("resource_changes", [])}


def actions(plan: dict) -> dict[str, list[str]]:
    return {address: r["change"]["actions"] for address, r in changes(plan).items()}


def swap_in(tofu, source: Path) -> None:
    for old in tofu.workdir.glob("*.tf"):
        old.unlink()
    for path in sorted(source.rglob("*")):
        if path.is_file() and ".terraform" not in path.parts and not path.name.endswith((".tfstate", ".tfstate.backup")):
            tofu.write(path.relative_to(source).as_posix(), path.read_text(encoding="utf-8"))


def create_legacy_bucket(prefix: str) -> None:
    s3 = localstack_client("s3")
    name = f"{prefix}-legacy-exports"
    s3.create_bucket(Bucket=name)
    s3.put_bucket_tagging(Bucket=name, Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in LEGACY_TAGS.items()]})
    s3.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": "Enabled"})


def cause_drift(prefix: str) -> None:
    s3 = localstack_client("s3")
    invoices = f"{prefix}-invoices"
    tags = s3.get_bucket_tagging(Bucket=invoices)["TagSet"]
    s3.put_bucket_tagging(Bucket=invoices, Tagging={"TagSet": [*tags, FINOPS_TAG]})
    s3.put_bucket_versioning(Bucket=f"{prefix}-reports", VersioningConfiguration={"Status": "Suspended"})


def unsafe(plan: dict) -> dict[str, list[str]]:
    return {address: acts for address, acts in actions(plan).items() if "create" in acts or "delete" in acts}


@pytest.fixture(scope="module")
def story():
    infra = ex.path("infra")
    with TofuLab(V1) as tofu:
        steps = {"lab": tofu}
        tofu.init()
        tofu.apply()
        create_legacy_bucket(tofu.prefix)
        swap_in(tofu, infra)
        init = tofu.init("-no-color", check=False)
        if init.returncode != 0:
            steps["error"] = f"tofu init với cấu hình của bạn lỗi:\n{tail(init)}"
            yield steps
            return
        plan = tofu.run("plan", "-input=false", "-no-color", "-out=refactor.tfplan", check=False)
        if plan.returncode != 0:
            steps["error"] = f"Plan refactor lỗi:\n{tail(plan)}"
            yield steps
            return
        steps["refactor"] = refactor = json.loads(tofu.run("show", "-json", "refactor.tfplan").stdout)
        if unsafe(refactor):
            steps["error"] = f"Plan refactor có tạo/xoá nên test không apply (không bao giờ apply plan phá dữ liệu): {unsafe(refactor)}"
            yield steps
            return
        steps["apply"] = tofu.run("apply", "-input=false", "-no-color", "refactor.tfplan", check=False)
        if steps["apply"].returncode != 0:
            steps["error"] = f"Apply plan refactor lỗi:\n{tail(steps['apply'])}"
            yield steps
            return
        try:
            steps["after_apply"] = tofu.plan("-no-color", "-detailed-exitcode", check=False)
            steps["state"] = set(tofu.state("list").stdout.split())
            cause_drift(tofu.prefix)
            steps["refresh_only"] = tofu.plan("-no-color", "-refresh-only", "-detailed-exitcode", check=False)
            steps["drift"] = tofu.plan_json("-no-color")
            steps["fix"] = tofu.apply("-no-color", check=False)
        except pytest.fail.Exception as error:
            steps["error"] = str(error)
        yield steps


def need(story, key):
    if key not in story:
        pytest.fail(story.get("error", f"Chưa tới bước {key}"))
    return story[key]


def test_refactor_never_creates_or_destroys(story):
    plan = need(story, "refactor")
    assert not unsafe(plan), f"Plan refactor không được tạo hay xoá tài nguyên nào: {unsafe(plan)}"


def test_refactor_moves_into_module(story):
    found = {address: r.get("previous_address") for address, r in changes(need(story, "refactor")).items()}
    wrong = {to: found.get(to) for to, source in MOVES.items() if found.get(to) != source}
    assert not wrong, f"Phải dời đúng địa chỉ cũ sang module.documents bằng moved (đích: nguồn đang thấy): {wrong}"


def test_refactor_imports_legacy_without_changes(story):
    plan = changes(need(story, "refactor"))
    for address in IMPORTS:
        assert address in plan and plan[address]["change"].get("importing"), f"{address} phải được import bằng khối import"
        assert plan[address]["change"]["actions"] == ["no-op"], (
            f"{address} import xong phải khớp thực tế (không update), plan đang đòi: {plan[address]['change']['actions']}")


def test_scratch_forgotten_not_destroyed(story):
    plan = actions(need(story, "refactor"))
    assert plan.get("aws_s3_bucket.scratch") == ["forget"], (
        f"aws_s3_bucket.scratch phải được bỏ khỏi state mà không xoá (removed + destroy = false), plan đang là {plan.get('aws_s3_bucket.scratch')}")
    need(story, "state")
    names = [b["Name"] for b in localstack_client("s3").list_buckets()["Buckets"]]
    assert f"{story['lab'].prefix}-scratch" in names, "Bucket scratch đã bị xoá thật"


def test_state_after_refactor(story):
    state = need(story, "state")
    assert state == STATE, f"State sau refactor phải đúng {sorted(STATE)}, đang là {sorted(state)}"
    result = story["after_apply"]
    assert result.returncode == 0, f"Sau refactor, plan phải 'No changes' (mã 0):\n{tail(result)}"


def test_drift_seen_by_refresh_only(story):
    result = need(story, "refresh_only")
    assert result.returncode == 2, f"plan -refresh-only phải thấy thay đổi ngoài OpenTofu (mã 2):\n{tail(result)}"


def test_drift_plan_only_restores_versioning(story):
    plan = {address: acts for address, acts in actions(need(story, "drift")).items() if acts not in (["no-op"], ["read"])}
    expected = {'module.documents.aws_s3_bucket_versioning.this["reports"]': ["update"]}
    assert plan == expected, f"Sau drift, plan chỉ được bật lại versioning của reports và bỏ qua tag cost-center: {plan}"


def test_drift_fixed_and_finops_tag_kept(story):
    result = need(story, "fix")
    assert result.returncode == 0, f"Apply sửa drift lỗi:\n{tail(result)}"
    s3 = localstack_client("s3")
    prefix = story["lab"].prefix
    assert s3.get_bucket_versioning(Bucket=f"{prefix}-reports").get("Status") == "Enabled", "Versioning của reports chưa được bật lại"
    tags = {t["Key"]: t["Value"] for t in s3.get_bucket_tagging(Bucket=f"{prefix}-invoices")["TagSet"]}
    assert tags.get("cost-center") == "fin-42", f"Tag cost-center do công cụ FinOps gắn đã bị xoá: {tags}"
