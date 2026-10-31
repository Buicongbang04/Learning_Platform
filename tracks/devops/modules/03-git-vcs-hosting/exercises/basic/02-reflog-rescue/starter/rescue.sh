#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <nhánh-đã-xoá>" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
deleted=$1

# TODO 1: trong reflog của main, tìm mục reset gần nhất; giá trị của main ngay TRƯỚC mục đó là tip đã mất
# TODO 2: trong reflog của HEAD, tìm lần gần nhất rời khỏi nhánh $deleted ("checkout: moving from $deleted to ...");
#         HEAD ngay trước mục đó là commit cuối của nhánh
# TODO 3: không tìm được một trong hai, hoặc nhánh đích đã tồn tại ở commit khác -> stderr, exit 1, không tạo nhánh nào
# TODO 4: tạo rescue/main và $deleted (không checkout, không reset), in "rescue/main <sha>" rồi "$deleted <sha>"

echo "deleted=$deleted" >&2
exit 1
