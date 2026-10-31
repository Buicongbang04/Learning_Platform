#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <thư mục>" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
root="$1"
[[ -d "$root" ]] || { echo "Không thấy thư mục: $root" >&2; exit 2; }

report() {
  local kind="$1"
  shift
  find . "$@" -printf "$kind %P\n"
}

findings="$(
  cd "$root"
  {
    report world-writable -type f -perm -0002
    report world-writable-dir -type d -perm -0002 ! -perm -1000
    report setuid -type f -perm -4000
    report setgid -type f -perm -2000
    report key-too-open -type f \( -name '*.key' -o -name 'id_*' \) ! -name '*.pub' -perm /0077
    report env-readable -type f \( -name '.env' -o -name '*.env' \) -perm /0007
  } | LC_ALL=C sort
)"

[[ -z "$findings" ]] && exit 0
printf '%s\n' "$findings"
exit 1
