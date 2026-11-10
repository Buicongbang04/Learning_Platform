import json
from concurrent.futures import ThreadPoolExecutor, wait

import shipping

MAX_IN_FLIGHT = 8
SAFETY_MS = 500
CALL_TIMEOUT = 2.0

POOL = ThreadPoolExecutor(max_workers=MAX_IN_FLIGHT)


def quote_record(record: dict) -> tuple[str, int]:
    order = json.loads(record["body"])
    return order["order_id"], shipping.quote(order["order_id"], timeout=CALL_TIMEOUT)


def handler(event, context):
    records = event.get("Records", [])
    futures = {POOL.submit(quote_record, record): record["messageId"] for record in records}
    budget = max(context.get_remaining_time_in_millis() - SAFETY_MS, 0) / 1000
    done, pending = wait(futures, timeout=budget)
    for future in pending:
        future.cancel()
    failures, quoted = [], 0
    for future, message_id in futures.items():
        if future in pending:
            failures.append({"itemIdentifier": message_id})
            print(json.dumps({"message_id": message_id, "error": "deadline"}))
        elif future.exception() is not None:
            failures.append({"itemIdentifier": message_id})
            print(json.dumps({"message_id": message_id, "error": str(future.exception())}))
        else:
            quoted += 1
    print(json.dumps({"quoted": quoted, "failed": len(failures)}))
    return {"batchItemFailures": failures}
