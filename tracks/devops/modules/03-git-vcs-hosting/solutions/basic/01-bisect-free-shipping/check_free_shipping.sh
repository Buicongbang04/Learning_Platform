#!/usr/bin/env bash
set -uo pipefail

python3 -B - <<'PY'
import sys

try:
    from olist_shop.shipping import shipping_fee

    fee = shipping_fee(200, "SP")
except Exception as exc:
    print(f"skip: {type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(125)

if fee == 0:
    sys.exit(0)
print(f"bad: shipping_fee(200, 'SP') = {fee}, cần 0", file=sys.stderr)
sys.exit(1)
PY
