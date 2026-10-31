#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <good-ref> <bad-ref>" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
good=$1
bad=$2

# TODO 1: git bisect start với bad và good; lỗi (ref sai, good không phải tổ tiên của bad) -> exit 1
# TODO 2: git bisect run bằng check_free_shipping.sh nằm cùng thư mục với script này (gọi qua bash)
# TODO 3: đọc commit lỗi đầu tiên từ refs/bisect/bad, in "first-bad <sha 40 ký tự>" ra stdout
# TODO 4: luôn git bisect reset, kể cả khi lỗi (trap), để repo quay về nhánh ban đầu

echo "good=$good bad=$bad" >&2
exit 1
