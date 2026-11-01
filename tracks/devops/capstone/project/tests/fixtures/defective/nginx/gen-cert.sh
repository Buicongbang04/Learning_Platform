#!/usr/bin/env bash
set -euo pipefail
out="$1"
mkdir -p "$out"
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=olist-shop.local" \
  -keyout "$out/olist-shop.key" -out "$out/olist-shop.crt" 2>/dev/null
chmod 644 "$out/olist-shop.key"
