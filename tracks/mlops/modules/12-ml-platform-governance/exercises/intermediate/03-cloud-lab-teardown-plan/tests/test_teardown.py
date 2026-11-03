import os
import stat
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
LAB = "ml-lab-7"
OWN = {"lab": LAB}

INVENTORY = [
    {"provider": "aws", "type": "s3-bucket", "name": "ml-lab-7-artifacts", "region": "ap-southeast-1", "tags": OWN},
    {"provider": "aws", "type": "sagemaker-model", "name": "ml-lab-7-eta", "region": "ap-southeast-1", "tags": OWN},
    {"provider": "aws", "type": "sagemaker-endpoint", "name": "ml-lab-7-eta", "region": "ap-southeast-1", "tags": OWN},
    {"provider": "aws", "type": "sagemaker-endpoint-config", "name": "ml-lab-7-eta", "region": "ap-southeast-1", "tags": OWN},
    {"provider": "aws", "type": "sagemaker-notebook", "name": "ml-lab-7-dev", "region": "ap-southeast-1", "tags": OWN},
    {"provider": "aws", "type": "nat-gateway", "name": "nat-0abc123", "region": "ap-southeast-1", "tags": OWN},
    {"provider": "aws", "type": "sagemaker-endpoint", "name": "ml-lab-7-hand-made", "region": "ap-southeast-1", "tags": {}},
    {"provider": "aws", "type": "sagemaker-endpoint", "name": "ml-lab-9-eta", "region": "ap-southeast-1", "tags": {"lab": "ml-lab-9"}},
    {"provider": "aws", "type": "s3-bucket", "name": "ml-lab-7-untagged-logs", "region": "ap-southeast-1", "tags": None},
    {"provider": "aws", "type": "s3-bucket", "name": "shared-data", "region": "ap-southeast-1"},
    {"provider": "gcp", "type": "vertex-endpoint", "name": "ml-lab-7-vx", "region": "asia-southeast1", "tags": OWN},
    {"provider": "gcp", "type": "vertex-model", "name": "ml-lab-7-vm", "region": "asia-southeast1", "tags": OWN},
    {"provider": "gcp", "type": "gcs-bucket", "name": "ml-lab-7-gcs", "region": "asia-southeast1", "tags": OWN},
    {"provider": "azure", "type": "azureml-endpoint", "name": "ml-lab-7-az", "region": "eastus", "resource_group": "rg-ml-lab-7", "tags": OWN},
    {"provider": "azure", "type": "azure-resource-group", "name": "rg-ml-lab-7", "region": "eastus", "tags": OWN},
]


@pytest.fixture
def td():
    return ex.module("teardown.py")


def commands(td, inventory=INVENTORY):
    return [s["command"] for s in td.plan_teardown(inventory, LAB)]


def test_only_resources_with_the_lab_tag_are_touched(td):
    steps = td.plan_teardown(INVENTORY, LAB)
    names = {s["resource"] for s in steps}
    assert "ml-lab-7-hand-made" not in names and "ml-lab-9-eta" not in names
    own = [i for i in INVENTORY if (i.get("tags") or {}).get("lab") == LAB]
    assert len(steps) == len(own) + 2
    assert all("hand-made" not in s["command"] and "lab-9" not in s["command"] for s in steps)


def test_exact_commands(td):
    cmds = commands(td)
    assert "aws sagemaker delete-endpoint --endpoint-name ml-lab-7-eta --region ap-southeast-1" in cmds
    assert "aws sagemaker delete-endpoint-config --endpoint-config-name ml-lab-7-eta --region ap-southeast-1" in cmds
    assert "aws sagemaker delete-model --model-name ml-lab-7-eta --region ap-southeast-1" in cmds
    assert "aws ec2 delete-nat-gateway --nat-gateway-id nat-0abc123 --region ap-southeast-1" in cmds
    assert "aws s3 rb s3://ml-lab-7-artifacts --force" in cmds
    assert "gcloud ai endpoints delete ml-lab-7-vx --region=asia-southeast1 --quiet" in cmds
    assert "gcloud ai models delete ml-lab-7-vm --region=asia-southeast1 --quiet" in cmds
    assert "gcloud storage rm --recursive gs://ml-lab-7-gcs" in cmds
    assert "az ml online-endpoint delete --name ml-lab-7-az --resource-group rg-ml-lab-7 --yes" in cmds
    assert "az group delete --name rg-ml-lab-7 --yes --no-wait" in cmds


def test_notebook_is_stopped_and_waited_before_deleted(td):
    cmds = commands(td)
    stop = cmds.index("aws sagemaker stop-notebook-instance --notebook-instance-name ml-lab-7-dev --region ap-southeast-1")
    wait = cmds.index("aws sagemaker wait notebook-instance-stopped --notebook-instance-name ml-lab-7-dev --region ap-southeast-1")
    delete = cmds.index("aws sagemaker delete-notebook-instance --notebook-instance-name ml-lab-7-dev --region ap-southeast-1")
    assert stop + 1 == wait and wait + 1 == delete


def test_order_serving_before_artifacts_and_storage_last(td):
    steps = td.plan_teardown(INVENTORY, LAB)
    types = [s["type"] for s in steps]
    order = td.ORDER
    assert types == sorted(types, key=order.index)
    assert types.index("sagemaker-endpoint") < types.index("sagemaker-endpoint-config") < types.index("sagemaker-model")
    assert types[-1] == "azure-resource-group"
    assert types.index("s3-bucket") > types.index("sagemaker-model")


def test_same_type_keeps_inventory_order(td):
    inv = [
        {"provider": "aws", "type": "s3-bucket", "name": "ml-lab-7-b", "region": "r", "tags": OWN},
        {"provider": "aws", "type": "s3-bucket", "name": "ml-lab-7-a", "region": "r", "tags": OWN},
    ]
    assert [s["resource"] for s in td.plan_teardown(inv, LAB)] == ["ml-lab-7-b", "ml-lab-7-a"]


def test_no_wildcards_or_force_except_bucket_removal(td):
    for command in commands(td):
        assert "*" not in command and "--all" not in command
        if "--force" in command:
            assert command.startswith("aws s3 rb s3://")


@pytest.mark.parametrize("bad", ["x; rm -rf /", "Name", "a b", "$(whoami)", "", "a" * 64, "-leading"])
def test_unsafe_names_are_rejected_by_name(td, bad):
    inv = [{"provider": "aws", "type": "s3-bucket", "name": bad, "region": "r", "tags": OWN}]
    with pytest.raises(ValueError):
        td.plan_teardown(inv, LAB)


@pytest.mark.parametrize("item", [
    {"provider": "aws", "type": "sagemaker-endpoint", "name": "ml-lab-7-eta", "region": "ap-southeast-1; rm -rf ~"},
    {"provider": "aws", "type": "sagemaker-model", "name": "ml-lab-7-eta", "region": "$(whoami)"},
    {"provider": "aws", "type": "sagemaker-model", "name": "ml-lab-7-eta"},
    {"provider": "gcp", "type": "vertex-endpoint", "name": "ml-lab-7-vx", "region": "asia-southeast1 --quiet; id"},
    {"provider": "azure", "type": "azureml-endpoint", "name": "ml-lab-7-az", "region": "eastus", "resource_group": "rg`id`"},
    {"provider": "azure", "type": "azureml-endpoint", "name": "ml-lab-7-az", "region": "eastus", "resource_group": "rg x"},
])
def test_unsafe_or_missing_region_and_resource_group_are_rejected(td, item):
    with pytest.raises(ValueError, match=item["name"]):
        td.plan_teardown([{**item, "tags": OWN}], LAB)


def test_unsafe_region_never_reaches_the_script(td, fake_cli, tmp_path):
    marker = tmp_path / "pwned"
    inv = INVENTORY + [{"provider": "aws", "type": "sagemaker-endpoint", "name": "ml-lab-7-x",
                        "region": f"ap-southeast-1; touch {marker}", "tags": OWN}]
    try:
        steps = td.plan_teardown(inv, LAB)
    except ValueError:
        return
    script = tmp_path / "teardown.sh"
    script.write_text(td.render_script(steps), encoding="utf-8")
    bin_dir, _ = fake_cli
    run_sandboxed(["bash", str(script)], writable=[tmp_path], cwd=tmp_path,
                  env={"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path)}, timeout=60)
    assert not marker.exists(), "region độc đã chạy như lệnh shell trong script dry-run"
    pytest.fail("plan_teardown phải từ chối region không khớp SAFE_NAME bằng ValueError")


def test_unsafe_name_of_another_lab_is_ignored_not_an_error(td):
    inv = [{"provider": "aws", "type": "s3-bucket", "name": "x; rm -rf /", "region": "r", "tags": {"lab": "other"}}]
    assert td.plan_teardown(inv, LAB) == []


def test_unknown_type_and_missing_resource_group(td):
    with pytest.raises(ValueError, match="quantum-box"):
        td.plan_teardown([{"provider": "aws", "type": "quantum-box", "name": "q", "region": "r", "tags": OWN}], LAB)
    with pytest.raises(ValueError, match="ml-lab-7-az"):
        td.plan_teardown([{"provider": "azure", "type": "azureml-endpoint", "name": "ml-lab-7-az", "region": "r", "tags": OWN}], LAB)


def test_empty_inventory_gives_empty_plan(td):
    assert td.plan_teardown([], LAB) == []


@pytest.fixture
def fake_cli(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    for tool in ("aws", "gcloud", "az"):
        path = bin_dir / tool
        path.write_text(
            "#!/usr/bin/env bash\n"
            f'echo "{tool} $*" >> "{log}"\n'
            'if [ -n "${FAIL_ON:-}" ] && [[ "$*" == *"$FAIL_ON"* ]]; then exit 3; fi\n'
        )
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return bin_dir, log


def run_script(td, fake_cli, tmp_path, dry=None, fail_on=None):
    bin_dir, log = fake_cli
    script = tmp_path / "teardown.sh"
    script.write_text(td.render_script(td.plan_teardown(INVENTORY, LAB)), encoding="utf-8")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path)}
    if dry is not None:
        env["DRY_RUN"] = dry
    if fail_on:
        env["FAIL_ON"] = fail_on
    done = run_sandboxed(["bash", str(script)], writable=[tmp_path], cwd=tmp_path, env=env, timeout=60)
    calls = log.read_text().splitlines() if log.exists() else []
    return done, calls


def test_script_header_and_run_lines(td):
    script = td.render_script(td.plan_teardown(INVENTORY, LAB))
    assert script.startswith("#!/usr/bin/env bash")
    assert sum(1 for line in script.splitlines() if line.startswith("run ")) == len(td.plan_teardown(INVENTORY, LAB))


def test_default_is_dry_run_and_calls_no_cli(td, fake_cli, tmp_path):
    done, calls = run_script(td, fake_cli, tmp_path)
    assert done.returncode == 0 and calls == []
    assert done.stdout.count("DRY-RUN: ") == len(td.plan_teardown(INVENTORY, LAB))
    assert "DRY-RUN: aws sagemaker delete-endpoint --endpoint-name ml-lab-7-eta" in done.stdout


def test_dry_run_one_is_still_dry(td, fake_cli, tmp_path):
    done, calls = run_script(td, fake_cli, tmp_path, dry="1")
    assert calls == [] and done.returncode == 0


def test_real_run_calls_each_command_in_plan_order(td, fake_cli, tmp_path):
    done, calls = run_script(td, fake_cli, tmp_path, dry="0")
    assert done.returncode == 0
    assert calls == [s["command"] for s in td.plan_teardown(INVENTORY, LAB)]


def test_failure_does_not_stop_the_rest_but_exits_nonzero(td, fake_cli, tmp_path):
    done, calls = run_script(td, fake_cli, tmp_path, dry="0", fail_on="delete-endpoint --endpoint-name")
    assert len(calls) == len(td.plan_teardown(INVENTORY, LAB))
    assert done.returncode != 0
    assert "FAILED: aws sagemaker delete-endpoint --endpoint-name ml-lab-7-eta" in done.stderr


def test_leftover_warns_about_hand_made_lookalikes(td):
    warnings = td.leftover_warnings(INVENTORY, LAB)
    assert [w["resource"] for w in warnings] == ["ml-lab-7-hand-made", "ml-lab-7-untagged-logs"]
    assert "tag" in warnings[0]["why"]


def test_leftover_needs_a_dash_boundary_after_the_lab_id(td):
    inv = [
        {"provider": "aws", "type": "sagemaker-endpoint", "name": "ml-lab-70-eta", "region": "r", "tags": {}},
        {"provider": "aws", "type": "s3-bucket", "name": "ml-lab-7", "region": "r", "tags": {}},
        {"provider": "aws", "type": "s3-bucket", "name": "ml-lab-7x", "region": "r", "tags": {}},
        {"provider": "aws", "type": "s3-bucket", "name": "ml-lab-7-old", "region": "r", "tags": {"lab": "ml-lab-70"}},
    ]
    assert [w["resource"] for w in td.leftover_warnings(inv, LAB)] == ["ml-lab-7", "ml-lab-7-old"]


def test_leftover_empty_when_everything_is_tagged(td):
    assert td.leftover_warnings([i for i in INVENTORY if (i.get("tags") or {}).get("lab") == LAB], LAB) == []
