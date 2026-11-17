#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Cách dùng: $0 VERSION [TÊN=GIÁ_TRỊ ...]" >&2
  exit 2
fi
version="$1"
shift

kubectl rollout pause deployment/api
if ! kubectl set env deployment/api "APP_VERSION=$version" "$@" ||
   ! kubectl annotate deployment/api "kubernetes.io/change-cause=release $version" --overwrite; then
  kubectl rollout resume deployment/api
  exit 1
fi
kubectl rollout resume deployment/api

if ! kubectl rollout status deployment/api --timeout=150s; then
  echo "Release $version không xong; bản cũ vẫn phục vụ. Xem kubectl rollout history deployment/api rồi chạy rollback.sh" >&2
  exit 1
fi
