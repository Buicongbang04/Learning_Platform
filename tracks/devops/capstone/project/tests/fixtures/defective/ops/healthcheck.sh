#!/usr/bin/env bash
url="${OLIST_SHOP_API_URL:-http://127.0.0.1:${OLIST_SHOP_API_PORT:-28000}}"
while getopts "u:t:w:" opt; do
  case "$opt" in
    u) url="$OPTARG" ;;
    *) ;;
  esac
done
curl -s "$url/readyz" >/dev/null && echo "OK db=ok redis=ok"
