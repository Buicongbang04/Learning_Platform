import json
import os

import boto3

LEDGER_TABLE = os.environ["LEDGER_TABLE"]
IDEMPOTENCY_TABLE = os.environ["IDEMPOTENCY_TABLE"]
KEEP_SECONDS = 7 * 24 * 3600

dynamodb = boto3.client("dynamodb")


class InvalidPayment(ValueError):
    pass


def parse(body: str) -> dict:
    data = json.loads(body)
    # TODO 1: body hỏng, thiếu trường hay amount_cents không phải số nguyên dương thì ném InvalidPayment.
    return {"payment_id": data["payment_id"], "seller_id": data["seller_id"], "amount_cents": data["amount_cents"]}


def credit(payment: dict) -> bool:
    # TODO 2: cùng một payment_id chỉ được cộng tiền một lần, kể cả khi hai message mang cùng payment_id.
    #         Trả False khi payment đã được ghi trước đó.
    dynamodb.update_item(
        TableName=LEDGER_TABLE,
        Key={"seller_id": {"S": payment["seller_id"]}},
        UpdateExpression="ADD balance_cents :amount, payments :one",
        ExpressionAttributeValues={":amount": {"N": str(payment["amount_cents"])}, ":one": {"N": "1"}},
    )
    return True


def handler(event, context):
    # TODO 3: một record lỗi không được làm cả batch chạy lại; trả {"batchItemFailures": [...]}.
    for record in event.get("Records", []):
        payment = parse(record["body"])
        credit(payment)
        print(json.dumps({"message_id": record["messageId"], "payment_id": payment["payment_id"]}))
    return {"batchItemFailures": []}
