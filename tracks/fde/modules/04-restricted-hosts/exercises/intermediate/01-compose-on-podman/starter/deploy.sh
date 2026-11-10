#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)

echo "deploy.sh: nạp image" >&2
docker load -i "$here/notice-image.tar"

echo "deploy.sh: chạy compose" >&2
"$here/docker-compose" -f "$here/compose.yaml" up -d --force-recreate
echo "deploy.sh: xong" >&2
