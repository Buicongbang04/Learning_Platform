import json
import os
import time

import boto3
from botocore.exceptions import ClientError

LEDGER_TABLE = os.environ["LEDGER_TABLE"]
IDEMPOTENCY_TABLE = os.environ["IDEMPOTENCY_TABLE"]
KEEP_SECONDS = 7 * 24 * 3600

dynamodb = boto3.client("dynamodb")


class InvalidPayment(ValueError):
    pass


def parse(body: str) -> dict:
    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        raise InvalidPayment("body không phải JSON") from error
    if not isinstance(data, dict):
        raise InvalidPayment("body phải là object")
    payment_id, seller_id, amount = data.get("payment_id"), data.get("seller_id"), data.get("amount_cents")
    if not isinstance(payment_id, str) or not payment_id or not isinstance(seller_id, str) or not seller_id:
        raise InvalidPayment("thiếu payment_id hoặc seller_id")
    if type(amount) is not int or amount <= 0:
        raise InvalidPayment("amount_cents phải là số nguyên dương")
    return {"payment_id": payment_id, "seller_id": seller_id, "amount_cents": amount}


def credit(payment: dict) -> bool:
    """Ghi nhận payment và cộng tiền cho seller trong cùng một transaction; trả False khi payment đã được ghi trước đó."""
    try:
        dynamodb.transact_write_items(TransactItems=[
            {"Put": {
                "TableName": IDEMPOTENCY_TABLE,
                "Item": {
                    "payment_id": {"S": payment["payment_id"]},
                    "seller_id": {"S": payment["seller_id"]},
                    "expires_at": {"N": str(int(time.time()) + KEEP_SECONDS)},
                },
                "ConditionExpression": "attribute_not_exists(payment_id)",
            }},
            {"Update": {
                "TableName": LEDGER_TABLE,
                "Key": {"seller_id": {"S": payment["seller_id"]}},
                "UpdateExpression": "ADD balance_cents :amount, payments :one",
                "ExpressionAttributeValues": {":amount": {"N": str(payment["amount_cents"])}, ":one": {"N": "1"}},
            }},
        ])
    except ClientError as error:
        reasons = error.response.get("CancellationReasons") or []
        if error.response["Error"]["Code"] == "TransactionCanceledException" and reasons \
                and reasons[0].get("Code") == "ConditionalCheckFailed":
            return False
        raise
    return True


def handler(event, context):
    failures = []
    for record in event.get("Records", []):
        message_id = record.get("messageId")
        try:
            payment = parse(record.get("body", ""))
            fresh = credit(payment)
        except Exception as error:
            print(json.dumps({"message_id": message_id, "error": type(error).__name__, "detail": str(error)}))
            failures.append({"itemIdentifier": message_id})
            continue
        print(json.dumps({"message_id": message_id, "payment_id": payment["payment_id"], "duplicate": not fresh}))
    return {"batchItemFailures": failures}
