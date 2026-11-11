import json
import re
from pathlib import Path

import pytest

from testkit import Exercise, TofuLab

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
VARS = {"owner": "ops@olist-shop.example", "expires_on": "2026-11-12", "alert_email": "ops@olist-shop.example"}
TAGS = {"Project": "olist-serverless-lab", "Owner": VARS["owner"], "ExpiresOn": VARS["expires_on"]}
FORBIDDEN = {"aws_nat_gateway", "aws_instance", "aws_db_instance", "aws_rds_cluster", "aws_eip", "aws_lb",
             "aws_apigatewayv2_api", "aws_lambda_provisioned_concurrency_config", "aws_elasticache_cluster"}
BAD = {"budget-50": {"monthly_budget_usd": 50}, "expires-sai": {"expires_on": "ngay-mai"}}
BUDGET_LIMIT = 5


def tail(result) -> str:
    return "\n".join(f"{result.stdout}\n{result.stderr}".strip().splitlines()[-40:])


@pytest.fixture(scope="module")
def planned():
    with TofuLab(ex.path("aws")) as tofu:
        tofu.write("ci.auto.tfvars.json", json.dumps(VARS))
        steps = {}
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
    return plan.get("planned_values", {}).get("root_module", {}).get("resources", [])


def all_of(plan: dict, type_: str) -> list[dict]:
    return [r["values"] for r in resources(plan) if r["type"] == type_]


def one(plan: dict, type_: str) -> dict:
    items = all_of(plan, type_)
    assert len(items) == 1, f"Cần đúng một {type_}, đang có {len(items)}"
    return items[0]


def configured(plan: dict, address: str) -> dict:
    for resource in plan.get("configuration", {}).get("root_module", {}).get("resources", []):
        if resource["address"] == address:
            return resource
    return {}


def test_plan_only_creates_cheap_resources(planned):
    plan = need(planned, "plan")
    actions = {r["address"]: r["change"]["actions"] for r in plan["resource_changes"] if r.get("mode") == "managed"}
    assert actions and all(a == ["create"] for a in actions.values()), actions
    types = {r["type"] for r in resources(plan)}
    assert not types & FORBIDDEN, f"Lab không cần tài nguyên tính tiền theo giờ hay HTTP API v2: {sorted(types & FORBIDDEN)}"
    for table in all_of(plan, "aws_dynamodb_table"):
        assert table.get("billing_mode") == "PAY_PER_REQUEST", f"Bảng {table.get('name')} dùng PAY_PER_REQUEST"


def test_budget_alarm(planned):
    budget = one(need(planned, "plan"), "aws_budgets_budget")
    assert budget["budget_type"] == "COST" and budget["time_unit"] == "MONTHLY" and budget["limit_unit"] == "USD", budget
    assert 0 < float(budget["limit_amount"]) <= 10, f"Budget phải ≤ 10 USD/tháng, đang là {budget['limit_amount']}"
    notes = {(n["notification_type"], n["threshold_type"], float(n["threshold"])) for n in budget.get("notification", [])}
    assert any(k[0] == "ACTUAL" and k[1] == "PERCENTAGE" and k[2] <= 80 for k in notes), f"Cần cảnh báo ACTUAL ≤ 80%: {sorted(notes)}"
    assert any(k[0] == "FORECASTED" and k[1] == "PERCENTAGE" and k[2] <= 100 for k in notes), \
        f"Cần cảnh báo FORECASTED ≤ 100%: {sorted(notes)}"
    for note in budget.get("notification", []):
        assert note["subscriber_email_addresses"] == [VARS["alert_email"]], "Cảnh báo gửi tới var.alert_email"


def test_lambda_small_bounded_and_logged(planned):
    plan = need(planned, "plan")
    function = one(plan, "aws_lambda_function")
    assert function.get("architectures") == ["arm64"], "Lambda chạy arm64 (Graviton, rẻ hơn khoảng 20% mỗi GB-giây)"
    assert (function.get("memory_size") or 128) <= 512 and (function.get("timeout") or 3) <= 30, \
        f"Lambda của lab: memory ≤ 512 MB, timeout ≤ 30 giây; đang là {function.get('memory_size')} MB, {function.get('timeout')} giây"
    mapping = one(plan, "aws_lambda_event_source_mapping")
    assert mapping.get("function_response_types") == ["ReportBatchItemFailures"], "Bật ReportBatchItemFailures"
    scaling = mapping.get("scaling_config") or [{}]
    assert 2 <= (scaling[0].get("maximum_concurrency") or 0) <= 5, "scaling_config.maximum_concurrency trong 2..5"
    groups = all_of(plan, "aws_cloudwatch_log_group")
    name = f"/aws/lambda/{function['function_name']}"
    assert any(g.get("name") == name and 1 <= (g.get("retention_in_days") or 0) <= 14 for g in groups), \
        f"Cần log group {name} với retention_in_days 1..14"
    queues = {q["name"]: q for q in all_of(plan, "aws_sqs_queue")}
    main = [q for q in queues.values() if not q["name"].endswith("-dlq")]
    assert main and all(q.get("visibility_timeout_seconds", 30) >= 6 * (function.get("timeout") or 3) for q in main), \
        "visibility_timeout_seconds của hàng đợi ≥ 6 lần timeout Lambda"


def test_dlq_with_alarm(planned):
    plan = need(planned, "plan")
    queue = configured(plan, "aws_sqs_queue.payments")
    refs = queue.get("expressions", {}).get("redrive_policy", {}).get("references", [])
    dlqs = {ref.split(".")[1] for ref in refs if ref.startswith("aws_sqs_queue.")}
    assert dlqs, "aws_sqs_queue.payments cần redrive_policy trỏ tới một hàng đợi DLQ"
    alarms = [a for a in plan.get("configuration", {}).get("root_module", {}).get("resources", [])
              if a["type"] == "aws_cloudwatch_metric_alarm"]
    watched = [a for a in alarms if any(f"aws_sqs_queue.{d}" in a.get("expressions", {}).get("dimensions", {}).get("references", [])
                                        for d in dlqs)]
    assert watched, "Cần aws_cloudwatch_metric_alarm theo dõi DLQ (dimensions QueueName lấy từ hàng đợi DLQ)"
    values = {r["address"]: r["values"] for r in resources(plan)}
    alarm = values[watched[0]["address"]]
    assert alarm.get("metric_name") == "ApproximateNumberOfMessagesVisible" and alarm.get("namespace") == "AWS/SQS", alarm
    assert alarm.get("comparison_operator") in ("GreaterThanThreshold", "GreaterThanOrEqualToThreshold"), alarm


def test_api_requires_key_with_quota_and_throttling(planned):
    plan = need(planned, "plan")
    methods = all_of(plan, "aws_api_gateway_method")
    assert methods and all(m.get("api_key_required") is True for m in methods), "Mọi method của API bắt buộc API key"
    integrations = all_of(plan, "aws_api_gateway_integration")
    assert integrations and all(i.get("type") in ("AWS", "AWS_PROXY", "MOCK") for i in integrations), \
        "Integration chỉ tới dịch vụ AWS (SQS, Lambda) hay MOCK, không proxy HTTP tới URL tuỳ ý"
    plans = all_of(plan, "aws_api_gateway_usage_plan")
    quota = [q for p in plans for q in p.get("quota_settings", []) if q.get("period") == "DAY" and 0 < q.get("limit", 0) <= 5000]
    assert quota, "Cần usage plan có quota theo ngày (≤ 5000 request)"
    assert all_of(plan, "aws_api_gateway_usage_plan_key"), "Gắn API key vào usage plan"
    settings = [s for m in all_of(plan, "aws_api_gateway_method_settings") for s in m.get("settings", [])]
    assert any(0 < (s.get("throttling_rate_limit") or 0) <= 10 and 0 < (s.get("throttling_burst_limit") or 0) <= 20 for s in settings), \
        "Stage cần throttling: rate ≤ 10 request/giây, burst ≤ 20"


def test_every_resource_tagged(planned):
    items = resources(need(planned, "plan"))
    tagged = [r for r in items if r["values"].get("tags_all") is not None]
    assert tagged, "Plan chưa có tài nguyên có tag nào"
    for resource in tagged:
        assert TAGS.items() <= resource["values"]["tags_all"].items(), f"{resource['address']} thiếu tag {TAGS}"


@pytest.mark.parametrize("case", sorted(BAD))
def test_validation(planned, case):
    result = need(planned, case)
    assert result.returncode != 0 and "Invalid value for variable" in f"{result.stdout}{result.stderr}", \
        f"Đầu vào {case} phải bị validation chặn:\n{tail(result)}"


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def code(text: str) -> str:
    return "\n".join(re.findall(r"```[a-z]*\n(.*?)```", text, re.S))


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:] if len(row) >= 4 and all(c.strip() for c in row[:4])]


def runbook_problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 8):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    cost = section(doc, 1)
    if len(table_rows(cost)) < 4:
        found.append("Phần 1: bảng chi phí cần ít nhất 4 dòng đủ 4 cột (Tài nguyên, Đơn giá, Lượng dùng, Thành tiền)")
    total = re.search(r"^.*Tổng.*?(\d+(?:[.,]\d+)?)\s*USD", cost, re.M)
    if not total:
        found.append("Phần 1: thiếu dòng 'Tổng ... <số> USD'")
    elif float(total.group(1).replace(",", ".")) > BUDGET_LIMIT:
        found.append(f"Phần 1: tổng ước tính vượt budget {BUDGET_LIMIT} USD của lab")
    if "free tier" not in cost.lower():
        found.append("Phần 1: chưa nói Free Tier có áp dụng hay không")
    budget = " ".join(section(doc, 2).lower().split())
    for words, message in ((("budget",), "budget"), (("forecast", "dự báo"), "cảnh báo dự báo"), (("email",), "email nhận cảnh báo")):
        if not any(w in budget for w in words):
            found.append(f"Phần 2: chưa nói tới {message}")
    deploy = code(section(doc, 3))
    if not re.search(r"tofu plan\b[^\n]*-out[= ]\S+", deploy) or not re.search(r"tofu apply\s+[\w./-]+\.tfplan", deploy):
        found.append("Phần 3: lưu plan bằng `tofu plan -out=<tệp>` rồi `tofu apply <tệp>.tfplan`, không apply cấu hình chưa review")
    if "get-caller-identity" not in deploy:
        found.append("Phần 3: kiểm đúng tài khoản sandbox (`aws sts get-caller-identity`) trước khi apply")
    if "auto-approve" in deploy:
        found.append("Phần 3: không dùng -auto-approve với tài khoản thật")
    check = section(doc, 4).lower()
    if "curl" not in check or "x-api-key" not in check:
        found.append("Phần 4: gọi API thật bằng curl có header x-api-key, và kiểm kết quả")
    cleanup = code(section(doc, 5))
    if "tofu destroy" not in cleanup:
        found.append("Phần 5: thiếu tofu destroy")
    if len(re.findall(r"(?:^|&&|\n)\s*aws \w+ (?:list|describe|get)-", cleanup)) < 2:
        found.append("Phần 5: cần ít nhất 2 lệnh `aws ... list/describe/get` kiểm không còn tài nguyên sau destroy")
    local = section(doc, 6).lower()
    if not any(w in local for w in ("localstack", "lambdalab")):
        found.append("Phần 6: chỉ cách chạy cùng luồng trên máy (LocalStack, LambdaLab)")
    if len(re.findall(r"^\s*-\s+\S", section(doc, 7), re.M)) < 3:
        found.append("Phần 7: ít nhất 3 gạch đầu dòng")
    return found


def test_runbook():
    found = runbook_problems(ex.read("RUNBOOK.md"))
    assert not found, "\n".join(found)


def test_runbook_checks_catch_template():
    found = runbook_problems((FIXTURES / "RUNBOOK.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and any(f.startswith("Phần 1: bảng chi phí") for f in found) and \
        any(f.startswith("Phần 5: thiếu tofu destroy") for f in found)


def test_runbook_checks_catch_weak_document():
    found = "\n".join(runbook_problems((FIXTURES / "RUNBOOK.weak.md").read_text(encoding="utf-8")))
    for needle in ("vượt budget", "Free Tier", "tofu apply <tệp>.tfplan", "get-caller-identity", "auto-approve", "x-api-key",
                   "thiếu tofu destroy", "Phần 6", "Phần 7"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
