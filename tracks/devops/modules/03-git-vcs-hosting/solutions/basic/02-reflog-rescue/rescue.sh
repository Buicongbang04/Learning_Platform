#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <nhánh-đã-xoá>" >&2
  exit 2
}

die() {
  echo "error: $*" >&2
  exit 1
}

[[ $# -eq 1 ]] || usage
deleted=$1
git check-ref-format "refs/heads/$deleted" || die "tên nhánh không hợp lệ: $deleted"

value_before() {
  local ref=$1 prefix=$2 previous_was_match=0 sha subject
  while IFS=$'\t' read -r sha subject; do
    if ((previous_was_match)); then
      printf '%s\n' "$sha"
      return 0
    fi
    [[ $subject == "$prefix"* ]] && previous_was_match=1
  done < <(git reflog show --format='%H%x09%gs' "$ref" --)
  return 1
}

lost_main=$(value_before refs/heads/main "reset: ") || die "reflog của main không có lần reset nào (hoặc reflog đã hết hạn)"
branch_tip=$(value_before HEAD "checkout: moving from $deleted to ") || die "reflog của HEAD không có lần rời nhánh $deleted"

check_free() {
  local name=$1 want=$2 have
  have=$(git rev-parse --verify --quiet "refs/heads/$name") || return 0
  [[ $have == "$want" ]] || die "nhánh $name đã tồn tại ở $have, không ghi đè"
}

check_free rescue/main "$lost_main"
check_free "$deleted" "$branch_tip"

git update-ref -m "rescue: main trước reset" refs/heads/rescue/main "$lost_main"
git update-ref -m "rescue: khôi phục $deleted" "refs/heads/$deleted" "$branch_tip"

echo "rescue/main $lost_main"
echo "$deleted $branch_tip"
