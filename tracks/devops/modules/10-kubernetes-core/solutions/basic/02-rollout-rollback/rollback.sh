#!/usr/bin/env bash
set -euo pipefail

if [ $# -gt 1 ]; then
  echo "Cách dùng: $0 [REVISION]" >&2
  exit 2
fi
if [ $# -eq 1 ]; then
  kubectl rollout undo deployment/api --to-revision="$1"
else
  kubectl rollout undo deployment/api
fi
kubectl rollout status deployment/api --timeout=150s
kubectl rollout history deployment/api
