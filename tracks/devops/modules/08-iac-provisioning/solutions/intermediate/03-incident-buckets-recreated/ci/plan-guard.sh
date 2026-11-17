#!/usr/bin/env bash
set -euo pipefail

plan_json="${1:?Cách dùng: plan-guard.sh <plan.json>}"
protected='["aws_s3_bucket","aws_dynamodb_table","aws_kms_key"]'
allowed="$(jq -n --arg list "${ALLOW_DESTROY:-}" '$list | split(" ") | map(select(length > 0))')"

blocked="$(jq -r --argjson protected "$protected" --argjson allowed "$allowed" '
  [.resource_changes[]?
   | select(.type as $t | $protected | index($t))
   | select(.change.actions | index("delete"))
   | select(.address as $a | $allowed | index($a) | not)
   | "\(.address) \(.change.actions | join(","))"]
  | .[]' "$plan_json")"

if [[ -n "$blocked" ]]; then
  echo "plan-guard: plan xoá hoặc thay thế tài nguyên giữ dữ liệu:" >&2
  echo "$blocked" >&2
  echo "Nếu thật sự muốn xoá, liệt kê địa chỉ trong ALLOW_DESTROY và ghi lý do trong PR." >&2
  exit 1
fi
echo "plan-guard: OK"
