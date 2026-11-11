#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Dùng: seal.sh <tệp Secret rõ, ngoài repo> <đường dẫn đích trong repo, đuôi .enc.yaml>" >&2
  exit 2
fi

plain=$1
target=$2

case "$target" in
  *.enc.yaml) ;;
  *) echo "Đích phải có đuôi .enc.yaml để khớp creation_rules và plugin của ArgoCD: $target" >&2; exit 2 ;;
esac

mkdir -p "$(dirname "$target")"
sops encrypt --filename-override "$target" --output "$target" "$plain"
