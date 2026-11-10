#!/usr/bin/env bash
set -euo pipefail

vault token create \
  -policy="$POLICY_NAME" \
  -ttl="${TOKEN_TTL:-15m}" \
  -explicit-max-ttl=1h \
  -display-name=olist-api \
  -field=token
