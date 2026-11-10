import json

import shipping


def handler(event, context):
    quotes = {}
    for record in event.get("Records", []):
        order = json.loads(record["body"])
        quotes[order["order_id"]] = shipping.quote(order["order_id"])
    print(json.dumps({"quoted": len(quotes)}))
    return {"batchItemFailures": []}
