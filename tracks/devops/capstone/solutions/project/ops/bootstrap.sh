#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-t chờ_tối_đa_giây]" >&2
  exit 2
}

log() {
  printf '%s bootstrap: %s\n' "$(date -u +%FT%TZ)" "$*" >&2
}

die() {
  log "$2"
  exit "$1"
}

wait_seconds=120
while getopts ":t:" opt; do
  case "$opt" in
    t) wait_seconds="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 0 ]] || usage
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || usage

ops_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

find_app_dir() {
  local dir="$ops_dir" candidate
  while :; do
    for candidate in "$dir/sample-app" "$dir/tracks/devops/sample-app"; do
      if [[ -f "$candidate/compose.yaml" ]]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done
    [[ "$dir" != / ]] || return 1
    dir="$(dirname -- "$dir")"
  done
}

env_file_value() {
  local line
  line="$(grep -E "^$1=" "$app_dir/.env" 2>/dev/null | tail -n 1)" || return 0
  line="${line#*=}"
  line="${line%\"}"
  line="${line#\"}"
  printf '%s' "$line"
}

app_dir="${OLIST_SHOP_APP_DIR:-}"
if [[ -z "$app_dir" ]]; then
  app_dir="$(find_app_dir)" || die 2 "không tìm thấy sample-app/compose.yaml; đặt OLIST_SHOP_APP_DIR"
fi
app_dir="$(cd -- "$app_dir" 2>/dev/null && pwd)" || die 2 "không vào được thư mục $app_dir"
compose_file="$app_dir/compose.yaml"
[[ -f "$compose_file" ]] || die 2 "không thấy $compose_file"
project="${OLIST_SHOP_PROJECT:-olist-shop}"
[[ "$project" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || die 2 "tên project compose không hợp lệ: $project"
command -v docker >/dev/null 2>&1 || die 2 "chưa cài docker"
docker compose version >/dev/null 2>&1 || die 2 "cần docker compose v2 (lệnh 'docker compose version' lỗi)"
[[ -f "$ops_dir/healthcheck.sh" ]] || die 2 "thiếu $ops_dir/healthcheck.sh"

if [[ ! -e "$app_dir/.env" && -f "$app_dir/.env.example" ]]; then
  cp -- "$app_dir/.env.example" "$app_dir/.env"
  log "đã tạo $app_dir/.env từ .env.example"
fi

port="${OLIST_SHOP_API_PORT:-$(env_file_value OLIST_SHOP_API_PORT)}"
port="${port:-28000}"
[[ "$port" =~ ^[0-9]+$ ]] || die 2 "OLIST_SHOP_API_PORT không hợp lệ: $port"
base_url="${OLIST_SHOP_API_URL:-http://127.0.0.1:$port}"

log "docker compose up project=$project file=$compose_file"
if ! docker compose --project-name "$project" --file "$compose_file" up --detach --build; then
  die 1 "docker compose up thất bại; xem: docker compose -p $project logs"
fi

log "chờ $base_url/readyz tối đa ${wait_seconds}s"
rc=0
status="$(bash "$ops_dir/healthcheck.sh" -u "$base_url" -w "$wait_seconds")" || rc=$?
if ((rc != 0)); then
  die 1 "chưa sẵn sàng sau ${wait_seconds}s: $status; xem: docker compose -p $project logs api"
fi
echo "ready $base_url"
