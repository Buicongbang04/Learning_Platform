#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-k số_bản_giữ] [-d thư_mục_đích]" >&2
  exit 2
}

log() {
  printf '%s backup: %s\n' "$(date -u +%FT%TZ)" "$*" >&2
}

dest="${OLIST_BACKUP_DIR:-backups}"
keep="${OLIST_BACKUP_KEEP:-5}"
while getopts ":k:d:" opt; do
  case "$opt" in
    k) keep="$OPTARG" ;;
    d) dest="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 0 ]] || usage
[[ "$keep" =~ ^[1-9][0-9]*$ ]] || usage
[[ "$dest" == / ]] || dest="${dest%/}"
[[ -n "$dest" ]] || usage

stamp="${BACKUP_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$stamp" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
  log "BACKUP_TIMESTAMP phải dạng YYYYMMDDTHHMMSSZ: $stamp"
  exit 2
fi

export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-${OLIST_SHOP_PG_PORT:-25432}}"
export PGUSER="${PGUSER:-olist}"
export PGDATABASE="${PGDATABASE:-olist}"

umask 077
mkdir -p -- "$dest"
exec 9>"$dest/.lock"
if ! flock -n 9; then
  log "một lần backup khác đang chạy trên $dest"
  exit 75
fi

find "$dest" -mindepth 1 -maxdepth 1 -type d -name '.inprogress-*' -exec rm -rf -- {} +

target="$dest/$stamp"

intact() {
  [[ -f "$1/olist.dump" && -f "$1/SHA256SUMS" ]] && (cd -- "$1" && sha256sum --status -c SHA256SUMS) 2>/dev/null
}

prune() {
  local name
  local -a old
  mapfile -t old < <(
    find "$dest" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended -regex '.*/[0-9]{8}T[0-9]{6}Z' -printf '%f\n' \
      | LC_ALL=C sort -r | tail -n +"$((keep + 1))"
  )
  for name in "${old[@]}"; do
    rm -rf -- "${dest:?}/$name"
    log "đã xoá bản cũ $name"
  done
}

if intact "$target"; then
  echo "skip $target"
  prune
  exit 0
fi

work=""
cleanup() {
  [[ -n "$work" ]] && rm -rf -- "$work"
  return 0
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

work="$(mktemp -d -- "$dest/.inprogress-$stamp.XXXXXX")"
if ! pg_dump --format=custom --file="$work/olist.dump"; then
  log "pg_dump thất bại cho $PGUSER@$PGHOST:$PGPORT/$PGDATABASE"
  exit 1
fi
if [[ ! -s "$work/olist.dump" ]]; then
  log "pg_dump tạo tệp rỗng"
  exit 1
fi
(cd -- "$work" && sha256sum olist.dump >SHA256SUMS)

if [[ -e "$target" ]]; then
  log "bản $stamp hỏng, tạo lại"
  rm -rf -- "$target"
fi
mv -T -- "$work" "$target"
work=""
echo "created $target"
prune
