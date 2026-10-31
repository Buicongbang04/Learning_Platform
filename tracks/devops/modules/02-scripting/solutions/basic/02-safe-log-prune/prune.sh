#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 -d <thư mục> -a <số ngày> [-p <glob>] [-n]" >&2
  exit 2
}

die() {
  echo "prune: $*" >&2
  exit 1
}

dir=""
days=""
pattern='*.log.*'
dry_run=0

while getopts ":d:a:p:n" opt; do
  case "$opt" in
    d) dir="$OPTARG" ;;
    a) days="$OPTARG" ;;
    p) pattern="$OPTARG" ;;
    n) dry_run=1 ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 0 && -n "$dir" && -n "$pattern" ]] || usage
[[ "$days" =~ ^[1-9][0-9]*$ ]] || usage

[[ -d "$dir" ]] || die "không thấy thư mục: $dir"
real="$(realpath -e -- "$dir")" || die "không giải được đường dẫn: $dir"
parts="${real//[^\/]/}"
if [[ "$real" == / || ${#parts} -lt 2 ]]; then
  die "từ chối xoá trong thư mục cấp cao: $real"
fi

verb="deleted"
((dry_run)) && verb="would delete"
count=0
while IFS= read -r -d '' file; do
  if ((!dry_run)); then
    rm -f -- "$file"
  fi
  printf '%s %s\n' "$verb" "$file"
  count=$((count + 1))
done < <(find "$dir" -xdev -type f -name "$pattern" -mtime +"$days" -print0)

echo "total=$count" >&2
