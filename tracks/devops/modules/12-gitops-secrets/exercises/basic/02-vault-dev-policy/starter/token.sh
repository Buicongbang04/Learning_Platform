#!/usr/bin/env bash
set -euo pipefail

# TODO: TTL mặc định 15 phút, đổi được bằng TOKEN_TTL; gia hạn tối đa 1 giờ (xem README)
vault token create -policy="$POLICY_NAME" -field=token
