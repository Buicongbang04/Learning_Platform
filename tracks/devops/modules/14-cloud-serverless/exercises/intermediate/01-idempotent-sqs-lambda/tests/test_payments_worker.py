import hashlib
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote

import pytest

from testkit import DockerLab, Exercise, LambdaLab, TofuLab, localstack_client

ex = Exercise(__file__)
LAMBDA_ONLY = ("aws_lambda_function.worker", "aws_lambda_event_source_mapping.payments")
OUTPUTS = ("queue_url", "dlq_url", "ledger_table", "idempotency_table")
SELLER_A = "3442f8959a84dea7ee197c632cb2df15"
SELLER_B = "d1b65fc7debc3361ea86b5f14c68d2e2"


@pytest.fixture(scope="module")
def stack():
    ex.require_localstack_devops("sqs", "dynamodb")
    state = {}
    with TofuLab(ex.path("infra")) as tofu:
        try:
            tofu.init("-no-color")
            state["plan"] = tofu.plan_json("-no-color")
            tofu.apply("-no-color", *[f"-exclude={address}" for address in LAMBDA_ONLY])
            outputs = tofu.output()
            missing = [name for name in OUTPUTS if name not in outputs]
            if missing:
                pytest.fail(f"Thiếu output {missing}")
            state["outputs"] = outputs
            state["prefix"] = tofu.prefix
        except pytest.fail.Exception as error:
            state["error"] = str(error)
        if "outputs" not in state:
            yield state
            return
        with DockerLab() as lab:
            env = {"LEDGER_TABLE": state["outputs"]["ledger_table"], "IDEMPOTENCY_TABLE": state["outputs"]["idempotency_table"]}
            with LambdaLab(lab, ex.path("handler"), "app.handler", env=env, timeout=10) as fn, \
                    LambdaLab(lab, ex.path("handler"), "app.handler", env=env, timeout=10, alias="lambda-b") as twin:
                state["fn"] = fn
                state["twin"] = twin
                yield state


def need(stack, key):
    if key not in stack:
        pytest.fail(stack.get("error", f"Chưa tới bước {key}"))
    return stack[key]


def configured(plan: dict, address: str) -> dict:
    for resource in plan.get("configuration", {}).get("root_module", {}).get("resources", []):
        if resource["address"] == address:
            return resource
    pytest.fail(f"Cấu hình chưa có {address}")


def values(plan: dict, address: str) -> dict:
    for resource in plan.get("planned_values", {}).get("root_module", {}).get("resources", []):
        if resource["address"] == address:
            return resource["values"]
    pytest.fail(f"Plan chưa có {address}")


def record(body, *, message_id: str | None = None, arn: str = "arn:aws:sqs:us-east-1:000000000000:payments") -> dict:
    text = body if isinstance(body, str) else json.dumps(body)
    now = str(int(time.time() * 1000))
    return {"messageId": message_id or str(uuid.uuid4()), "receiptHandle": uuid.uuid4().hex, "body": text,
            "attributes": {"ApproximateReceiveCount": "1", "SentTimestamp": now, "SenderId": "AIDAEXAMPLE",
                           "ApproximateFirstReceiveTimestamp": now},
            "messageAttributes": {}, "md5OfBody": hashlib.md5(text.encode()).hexdigest(), "eventSource": "aws:sqs",
            "eventSourceARN": arn, "awsRegion": "us-east-1"}


def payment(seller: str, cents: int) -> dict:
    return {"payment_id": f"pay-{uuid.uuid4().hex[:12]}", "seller_id": seller, "amount_cents": cents}


def ledger(stack, seller: str) -> tuple[int, int]:
    item = localstack_client("dynamodb").get_item(TableName=stack["outputs"]["ledger_table"],
                                                   Key={"seller_id": {"S": seller}}, ConsistentRead=True).get("Item", {})
    return int(item.get("balance_cents", {}).get("N", 0)), int(item.get("payments", {}).get("N", 0))


def failures(result) -> set[str]:
    assert isinstance(result, dict) and "batchItemFailures" in result, \
        f"Handler phải trả {{'batchItemFailures': [...]}}, đang trả {str(result)[:500]}"
    return {item.get("itemIdentifier") for item in result["batchItemFailures"]}


def test_queue_has_dlq_and_long_enough_visibility(stack):
    plan = need(stack, "plan")
    queue = values(plan, "aws_sqs_queue.payments")
    function = values(plan, "aws_lambda_function.worker")
    timeout = function.get("timeout") or 3
    assert queue.get("visibility_timeout_seconds", 30) >= 6 * timeout, \
        f"visibility_timeout_seconds ({queue.get('visibility_timeout_seconds', 30)}) cần ít nhất 6 lần timeout của Lambda ({timeout})"
    expression = configured(plan, "aws_sqs_queue.payments").get("expressions", {}).get("redrive_policy", {})
    assert "aws_sqs_queue.payments_dlq" in expression.get("references", []), "redrive_policy phải trỏ aws_sqs_queue.payments_dlq"
    dlq = values(plan, "aws_sqs_queue.payments_dlq")
    assert dlq.get("message_retention_seconds", 345600) > queue.get("message_retention_seconds", 345600), \
        "DLQ phải giữ message lâu hơn hàng đợi nguồn (tuổi message tính từ lúc gửi vào hàng đợi nguồn)"


def test_event_source_mapping_reports_partial_failures(stack):
    mapping = values(need(stack, "plan"), "aws_lambda_event_source_mapping.payments")
    assert mapping.get("function_response_types") == ["ReportBatchItemFailures"], "Bật ReportBatchItemFailures"
    assert 1 <= (mapping.get("batch_size") or 10) <= 10, "batch_size tối đa 10"
    scaling = mapping.get("scaling_config") or [{}]
    assert 2 <= (scaling[0].get("maximum_concurrency") or 0) <= 20, "Đặt scaling_config.maximum_concurrency trong 2..20"
    function = configured(need(stack, "plan"), "aws_lambda_function.worker")
    env = json.dumps(function.get("expressions", {}).get("environment", []))
    assert "aws_dynamodb_table.ledger" in env and "aws_dynamodb_table.idempotency" in env, \
        "Biến LEDGER_TABLE, IDEMPOTENCY_TABLE của Lambda lấy từ hai bảng"


def as_list(value) -> list:
    if value is None:
        return []
    return [value] if isinstance(value, (str, dict)) else list(value)


def policy_problems(statements: list[dict]) -> list[str]:
    problems = []
    for statement in statements:
        if statement.get("Effect") != "Allow":
            continue
        if "NotAction" in statement or "NotResource" in statement:
            problems.append("Allow kèm NotAction/NotResource")
        for action in as_list(statement.get("Action")):
            if "*" in action or "?" in action:
                problems.append(f"Action {action} có wildcard")
        if "*" in as_list(statement.get("Resource")):
            problems.append("Resource \"*\"")
    return problems


def test_policy_checks_catch_wide_grants():
    for statement in ({"Effect": "Allow", "Action": "dynamodb:*", "Resource": "arn:aws:dynamodb:us-east-1:1:table/t"},
                      {"Effect": "Allow", "Action": "dynamodb:Put*", "Resource": "arn:aws:dynamodb:us-east-1:1:table/t"},
                      {"Effect": "Allow", "Action": "sqs:ReceiveMessage", "Resource": "*"},
                      {"Effect": "Allow", "NotAction": "iam:*", "Resource": "arn:aws:sqs:us-east-1:1:q"}):
        assert policy_problems([statement]), f"Bộ kiểm không bắt được {statement}"
    assert not policy_problems([{"Effect": "Allow", "Action": ["dynamodb:PutItem"], "Resource": "arn:aws:dynamodb:us-east-1:1:table/t"}])


def test_worker_policy_scoped(stack):
    need(stack, "outputs")
    iam = localstack_client("iam")
    role = f"{stack['prefix']}-payments-worker"
    names = iam.list_role_policies(RoleName=role)["PolicyNames"]
    statements = []
    for name in names:
        document = iam.get_role_policy(RoleName=role, PolicyName=name)["PolicyDocument"]
        document = document if isinstance(document, dict) else json.loads(unquote(document))
        found = document.get("Statement", [])
        statements += [found] if isinstance(found, dict) else found
    problems = policy_problems(statements)
    assert statements, f"Role {role} chưa có inline policy nào"
    assert not problems, f"Policy của worker quá rộng: {problems}"


def test_idempotency_table_expires_records(stack):
    need(stack, "outputs")
    table = stack["outputs"]["idempotency_table"]
    ttl = localstack_client("dynamodb").describe_time_to_live(TableName=table)["TimeToLiveDescription"]
    assert ttl.get("TimeToLiveStatus") == "ENABLED" and ttl.get("AttributeName") == "expires_at", f"Bật TTL theo expires_at: {ttl}"


def test_same_payment_credited_once(stack):
    fn = need(stack, "fn")
    first, second = payment(SELLER_A, 12990), payment(SELLER_A, 4550)
    batch = [record(first), record(second), record(first)]
    result = fn.invoke({"Records": batch})
    assert failures(result) == set(), f"Payment hợp lệ không được báo lỗi: {result}"
    redelivered = fn.invoke({"Records": [record(first, message_id=batch[0]["messageId"]), record(second)]})
    assert failures(redelivered) == set(), f"Payment đã xử lý không được báo lỗi khi nhận lại: {redelivered}"
    assert ledger(stack, SELLER_A) == (12990 + 4550, 2), \
        f"Seller phải được cộng đúng hai payment một lần, đang là (balance_cents, payments) = {ledger(stack, SELLER_A)}"


def test_bad_records_reported_alone(stack):
    fn = need(stack, "fn")
    good = record(payment(SELLER_B, 2500))
    bad = [record({"payment_id": "pay-negative", "seller_id": SELLER_B, "amount_cents": -5}), record("{not json"),
           record({"payment_id": "pay-float", "seller_id": SELLER_B, "amount_cents": 10.5}), record({"seller_id": SELLER_B})]
    result = fn.invoke({"Records": [bad[0], good, *bad[1:]]})
    assert failures(result) == {r["messageId"] for r in bad}, f"Chỉ record hỏng nằm trong batchItemFailures: {result}"
    assert ledger(stack, SELLER_B) == (2500, 1), f"Record hợp lệ trong cùng batch vẫn được cộng: {ledger(stack, SELLER_B)}"


def test_poison_message_lands_in_dlq(stack):
    fn = need(stack, "fn")
    sqs = localstack_client("sqs")
    queue, dlq = stack["outputs"]["queue_url"], stack["outputs"]["dlq_url"]
    attributes = sqs.get_queue_attributes(QueueUrl=queue, AttributeNames=["All"])["Attributes"]
    assert "RedrivePolicy" in attributes, "Hàng đợi payments chưa có redrive policy"
    limit = int(json.loads(attributes["RedrivePolicy"])["maxReceiveCount"])
    assert 2 <= limit <= 5, f"maxReceiveCount nên trong 2..5, đang là {limit}"
    seller = uuid.uuid4().hex
    good = payment(seller, 1000)
    poison = json.dumps({"payment_id": "pay-poison", "seller_id": seller, "amount_cents": "1000"})
    sqs.send_message(QueueUrl=queue, MessageBody=json.dumps(good))
    sqs.send_message(QueueUrl=queue, MessageBody=poison)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        messages = sqs.receive_message(QueueUrl=queue, MaxNumberOfMessages=10, WaitTimeSeconds=1, VisibilityTimeout=0,
                                       AttributeNames=["All"]).get("Messages", [])
        if not messages:
            break
        event = {"Records": [record(m["Body"], message_id=m["MessageId"], arn=attributes["QueueArn"]) for m in messages]}
        failed = failures(fn.invoke(event))
        for message in messages:
            if message["MessageId"] not in failed:
                sqs.delete_message(QueueUrl=queue, ReceiptHandle=message["ReceiptHandle"])
    else:
        pytest.fail("Hàng đợi payments vẫn còn message sau 60 giây")
    dead = sqs.receive_message(QueueUrl=dlq, MaxNumberOfMessages=10, WaitTimeSeconds=2).get("Messages", [])
    assert [m["Body"] for m in dead] == [poison], f"DLQ phải có đúng message hỏng, đang có {len(dead)} message"
    assert ledger(stack, seller) == (1000, 1), f"Payment hợp lệ được cộng đúng một lần: {ledger(stack, seller)}"


def test_parallel_deliveries_credit_once(stack):
    fn, twin = need(stack, "fn"), need(stack, "twin")
    seller = uuid.uuid4().hex
    payments = [payment(seller, 100 + i) for i in range(10)]
    events = [{"Records": [record(p) for p in payments]} for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: pair[0].invoke(pair[1]), zip((fn, twin), events)))
    for result in results:
        assert failures(result) == set(), f"Payment hợp lệ không được báo lỗi: {result}"
    expected = (sum(p["amount_cents"] for p in payments), len(payments))
    assert ledger(stack, seller) == expected, \
        f"Hai Lambda nhận cùng batch cùng lúc: mỗi payment chỉ được cộng một lần, mong đợi {expected}, đang là {ledger(stack, seller)}"
