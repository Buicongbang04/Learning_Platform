#!/usr/bin/env bash
set -euo pipefail

target=secrets/olist-db.enc.yaml

if [ -t 0 ]; then
  echo "Dùng: seal-db.sh < tệp-chứa-mật-khẩu (đọc mật khẩu Postgres từ stdin, không nhận qua tham số)" >&2
  exit 2
fi
IFS= read -r password || true
if [ -z "$password" ]; then
  echo "stdin rỗng: cần một dòng mật khẩu Postgres" >&2
  exit 2
fi
case "$password" in
  *[!A-Za-z0-9_-]*) echo "Mật khẩu chỉ gồm A-Z, a-z, 0-9, '_' và '-' (nằm thẳng trong DATABASE_URL)" >&2; exit 2 ;;
esac

umask 077
mkdir -p "$(dirname "$target")"
staged=$(mktemp "$(dirname "$target")/.olist-db.XXXXXX")
trap 'rm -f "$staged"' EXIT

printf '%s\n' \
  "apiVersion: v1" \
  "kind: Secret" \
  "metadata:" \
  "  name: olist-db" \
  "type: Opaque" \
  "stringData:" \
  "  POSTGRES_USER: olist" \
  "  POSTGRES_DB: olist" \
  "  POSTGRES_PASSWORD: \"$password\"" \
  "  DATABASE_URL: \"postgresql+psycopg://olist:$password@postgres:5432/olist\"" |
  sops encrypt --filename-override "$target" --input-type yaml --output-type yaml --output "$staged" /dev/stdin
mv "$staged" "$target"
echo "Đã ghi $target"
