import json
import re

import pytest

from testkit import Exercise, TofuLab

ex = Exercise(__file__)
VARS = {"owner": "ops@olist-shop.example", "expires_on": "2026-11-08", "alert_email": "ops@olist-shop.example",
        "ami_id": "ami-0abcdef1234567890"}
DEFAULT_TAGS = {"Project": "olist-shop-sandbox", "Owner": VARS["owner"], "ExpiresOn": VARS["expires_on"]}
FORBIDDEN_TYPES = {"aws_internet_gateway", "aws_nat_gateway", "aws_eip", "aws_lb", "aws_db_instance"}
BAD = {
    "budget-50": {"monthly_budget_usd": 50},
    "instance-m5": {"instance_type": "m5.large"},
    "ami-sai": {"ami_id": "ubuntu-latest"},
}


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


@pytest.fixture(scope="module")
def planned():
    with TofuLab(ex.path("aws")) as tofu:
        tofu.write("ci.auto.tfvars.json", json.dumps(VARS))
        steps = {"lab": tofu}
        init = tofu.init("-no-color", check=False)
        if init.returncode != 0:
            steps["error"] = f"tofu init lỗi:\n{tail(init)}"
            yield steps
            return
        try:
            steps["plan"] = tofu.plan_json("-no-color")
            for case, override in BAD.items():
                path = tofu.write("zz-bad.auto.tfvars.json", json.dumps({**VARS, **override}))
                steps[case] = tofu.plan("-no-color", check=False)
                path.unlink()
        except pytest.fail.Exception as error:
            steps["error"] = str(error)
        yield steps


def need(steps, key):
    if key not in steps:
        pytest.fail(steps.get("error", f"Chưa tới bước {key}"))
    return steps[key]


def resources(plan: dict) -> list[dict]:
    found, stack = [], [plan.get("planned_values", {}).get("root_module", {})]
    while stack:
        module = stack.pop()
        found += module.get("resources", [])
        stack += module.get("child_modules", [])
    return found


def one(plan: dict, type_: str) -> dict:
    items = [r for r in resources(plan) if r["type"] == type_]
    assert len(items) == 1, f"Cần đúng một {type_}, đang có {len(items)}"
    return items[0]["values"]


def test_plan_only_creates(planned):
    plan = need(planned, "plan")
    acts = {r["address"]: r["change"]["actions"] for r in plan["resource_changes"]}
    assert acts and all(a == ["create"] for a in acts.values()), acts


def test_budget_alarm(planned):
    budget = one(need(planned, "plan"), "aws_budgets_budget")
    assert budget["budget_type"] == "COST" and budget["time_unit"] == "MONTHLY" and budget["limit_unit"] == "USD", budget
    assert 0 < float(budget["limit_amount"]) <= 10, f"Budget phải ≤ 10 USD/tháng, đang là {budget['limit_amount']}"
    notes = {(n["notification_type"], n["threshold_type"], float(n["threshold"])): n for n in budget.get("notification", [])}
    actual = [k for k in notes if k[0] == "ACTUAL" and k[1] == "PERCENTAGE" and k[2] <= 80]
    forecast = [k for k in notes if k[0] == "FORECASTED" and k[1] == "PERCENTAGE" and k[2] <= 100]
    assert actual and forecast, f"Cần cảnh báo ACTUAL ≤ 80% và FORECASTED ≤ 100%, đang có {sorted(notes)}"
    for note in notes.values():
        assert note["subscriber_email_addresses"] == [VARS["alert_email"]], "Cảnh báo phải gửi tới var.alert_email"


def test_instance_is_small_private_hardened(planned):
    instance = one(need(planned, "plan"), "aws_instance")
    assert instance["instance_type"] in ("t4g.nano", "t4g.micro"), instance["instance_type"]
    assert instance.get("associate_public_ip_address") is False, "Instance không được có IP public"
    assert instance["metadata_options"][0]["http_tokens"] == "required", "Bắt buộc IMDSv2 (http_tokens = required)"
    root = instance["root_block_device"][0]
    assert root.get("encrypted") is True and root.get("volume_size", 99) <= 8, f"Ổ root phải mã hoá và ≤ 8 GiB: {root}"


def test_private_network_without_paid_extras(planned):
    plan = need(planned, "plan")
    types = {r["type"] for r in resources(plan)}
    assert not types & FORBIDDEN_TYPES, f"Sandbox không cần (và không được tạo) tài nguyên tính phí giờ: {sorted(types & FORBIDDEN_TYPES)}"
    subnets = [r["values"] for r in resources(plan) if r["type"] == "aws_subnet"]
    assert subnets and all(s.get("map_public_ip_on_launch") is False for s in subnets), "Subnet phải private"


def test_every_resource_tagged(planned):
    items = resources(need(planned, "plan"))
    assert any(r["values"].get("tags_all") is not None for r in items), "Plan chưa có tài nguyên có tag nào"
    for resource in items:
        tags = resource["values"].get("tags_all")
        if tags is None:
            continue
        assert DEFAULT_TAGS.items() <= tags.items(), f"{resource['address']} thiếu tag {DEFAULT_TAGS}: {tags}"


@pytest.mark.parametrize("case", sorted(BAD))
def test_validation(planned, case):
    result = need(planned, case)
    assert result.returncode != 0 and "Invalid value for variable" in f"{result.stdout}{result.stderr}", (
        f"Đầu vào {case} phải bị validation chặn:\n{tail(result)}")


def cost_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:] if len(row) >= 4 and all(c.strip() for c in row[:4])]


def cost_problems(text: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in text else []
    rows = cost_rows(text)
    if len(rows) < 3:
        found.append("Bảng chi phí cần ít nhất 3 dòng đủ 4 cột (Tài nguyên, Đơn giá, Thời gian, Thành tiền)")
    total = re.search(r"^.*Tổng.*?(\d+(?:[.,]\d+)?)\s*USD", text, re.M | re.I)
    if not total:
        found.append("Thiếu dòng 'Tổng ... <số> USD'")
    elif float(total.group(1).replace(",", ".")) > 10:
        found.append("Tổng chi phí ước tính vượt budget 10 USD")
    for word, message in (("tofu destroy", "Thiếu bước tofu destroy"), ("budget", "Thiếu phần budget"),
                          ("free tier", "Chưa nói Free Tier có áp dụng hay không")):
        if word not in text.lower():
            found.append(message)
    return found


def test_cost_estimate():
    found = cost_problems(ex.read("COST.md"))
    assert not found, "\n".join(found)


def test_cost_checks_catch_template():
    found = cost_problems((ex.dir / "starter" / "COST.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and any(p.startswith("Bảng chi phí") for p in found) and "Thiếu dòng 'Tổng ... <số> USD'" in found
