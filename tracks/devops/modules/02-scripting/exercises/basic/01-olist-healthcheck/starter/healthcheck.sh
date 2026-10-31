#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-u base_url] [-t timeout_giây]" >&2
  exit 3
}

base_url="${OLIST_SHOP_API_URL:-http://localhost:${OLIST_SHOP_API_PORT:-28000}}"
timeout=3

# TODO 1: đọc -u và -t bằng getopts; -t là số nguyên >= 1; option lạ hoặc tham số thừa thì usage
# TODO 2: gọi GET /healthz bằng curl có --max-time; curl lỗi -> "CRITICAL - api unreachable (curl exit N)", exit 2
#         (nhớ: với set -e, lệnh lỗi làm script chết trước khi kịp in gì)
# TODO 3: /healthz khác 200 -> "CRITICAL - healthz=<code>", exit 2, không gọi /readyz
# TODO 4: gọi GET /readyz, đọc db và redis bằng jq, in một dòng OK/WARNING/CRITICAL/UNKNOWN theo bảng trong đề

echo "UNKNOWN - chưa viết (url=$base_url timeout=$timeout)"
usage
