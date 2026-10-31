#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-k số_bản_giữ] <thư_mục_backup>" >&2
  exit 2
}

log() {
  printf '%s backup: %s\n' "$(date -u +%FT%TZ)" "$*" >&2
}

keep=7
backup_date="${BACKUP_DATE:-$(date -u +%F)}"

while getopts ":k:" opt; do
  case "$opt" in
    k) keep="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 1 && -n "$1" ]] || usage
[[ "$keep" =~ ^[1-9][0-9]*$ ]] || usage
dir="${1%/}"
if [[ ! "$backup_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  log "BACKUP_DATE phải dạng YYYY-MM-DD: $backup_date"
  exit 2
fi

export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-25432}"
export PGUSER="${PGUSER:-olist}"
export PGDATABASE="${PGDATABASE:-olist}"

umask 077
mkdir -p -- "$dir"
exec 9>"$dir/.backup.lock"
if ! flock -n 9; then
  log "một bản backup khác đang chạy trên $dir"
  exit 75
fi

name="olist-$backup_date.dump"
target="$dir/$name"

if [[ -f "$target" && -f "$target.sha256" ]] && (cd -- "$dir" && sha256sum --status -c -- "$name.sha256") 2>/dev/null; then
  echo "skip $target"
  exit 0
fi

tmp=""
cleanup() {
  [[ -n "$tmp" ]] && rm -f -- "$tmp" "$tmp.sha256"
  return 0
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

tmp="$(mktemp -- "$dir/.$name.XXXXXX")"
if ! pg_dump --format=custom --file="$tmp"; then
  log "pg_dump thất bại cho $PGUSER@$PGHOST:$PGPORT/$PGDATABASE"
  exit 1
fi
if [[ ! -s "$tmp" ]]; then
  log "pg_dump tạo tệp rỗng"
  exit 1
fi

digest="$(sha256sum -- "$tmp")"
printf '%s  %s\n' "${digest%% *}" "$name" >"$tmp.sha256"
mv -f -- "$tmp" "$target"
mv -f -- "$tmp.sha256" "$target.sha256"
tmp=""
echo "created $target"

mapfile -t old < <(
  find "$dir" -maxdepth 1 -type f -name 'olist-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].dump' -printf '%f\n' \
    | LC_ALL=C sort -r | tail -n +"$((keep + 1))"
)
for file in "${old[@]}"; do
  rm -f -- "$dir/$file" "$dir/$file.sha256"
  log "đã xoá bản cũ $file"
done
