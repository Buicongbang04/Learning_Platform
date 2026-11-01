#!/usr/bin/env bash
app="${OLIST_SHOP_APP_DIR:?}"
project="${OLIST_SHOP_PROJECT:-olist-shop}"
if [ -f "$app/.env" ]; then . "$app/.env"; fi
port="$(grep '^OLIST_SHOP_API_PORT=' "$app/.env.example" | cut -d= -f2)"
docker compose -p "$project" -f "$app/compose.yaml" down -v
cp "$app/.env.example" "$app/.env"
docker compose -p "$project" -f "$app/compose.yaml" up -d
echo "ready http://127.0.0.1:$port"
