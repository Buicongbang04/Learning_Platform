#!/usr/bin/env bash
set -euo pipefail

plan_json="${1:?Cách dùng: plan-guard.sh <plan.json>}"
test -r "$plan_json"
echo "plan-guard: OK"
