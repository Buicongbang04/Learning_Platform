#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Dùng: seal.sh <tệp Secret rõ, ngoài repo> <đường dẫn đích trong repo, đuôi .enc.yaml>" >&2
  exit 2
fi

# TODO: mã hoá $1 thành $2 theo creation_rules của .sops.yaml (rule chọn theo đường dẫn đích), không ghi bản rõ vào repo
echo "TODO: seal.sh chưa viết" >&2
exit 1
