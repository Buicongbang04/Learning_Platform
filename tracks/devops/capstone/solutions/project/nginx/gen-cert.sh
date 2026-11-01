#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <thư_mục_đích>" >&2
  exit 2
}

log() {
  printf '%s gen-cert: %s\n' "$(date -u +%FT%TZ)" "$*" >&2
}

[[ $# -eq 1 && -n "$1" ]] || usage
out="${1%/}"
out="${out:-/}"
crt="$out/olist-shop.crt"
key="$out/olist-shop.key"
renew_before=$((30 * 24 * 3600))

usable() {
  [[ -f "$crt" && -f "$key" ]] || return 1
  openssl x509 -in "$crt" -noout -checkend "$renew_before" >/dev/null 2>&1 || return 1
  local cert_pub key_pub
  cert_pub="$(openssl x509 -in "$crt" -noout -pubkey 2>/dev/null)" || return 1
  key_pub="$(openssl pkey -in "$key" -pubout 2>/dev/null)" || return 1
  [[ "$cert_pub" == "$key_pub" ]]
}

umask 077
mkdir -p -- "$out"
if usable; then
  log "giữ nguyên $crt (còn hạn hơn 30 ngày, khớp key)"
  exit 0
fi

work="$(mktemp -d -- "$out/.gen-cert.XXXXXX")"
trap 'rm -rf -- "$work"' EXIT

openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 365 -sha256 \
  -subj "/CN=olist-shop.local" \
  -addext "subjectAltName=DNS:olist-shop.local,DNS:localhost,IP:127.0.0.1" \
  -addext "extendedKeyUsage=serverAuth" \
  -keyout "$work/olist-shop.key" -out "$work/olist-shop.crt" 2>/dev/null
chmod 600 "$work/olist-shop.key"
chmod 644 "$work/olist-shop.crt"
mv -f -- "$work/olist-shop.key" "$key"
mv -f -- "$work/olist-shop.crt" "$crt"
log "đã tạo $crt (tự ký, 365 ngày)"
