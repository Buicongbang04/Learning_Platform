#!/bin/sh
set -u

bundle=$(cd "$(dirname "$0")" && pwd)
conf=$bundle/site.conf
project=quillo
services="db llm embed api worker"
failed=0

ok() { echo "verify: OK   $*"; }
bad() { echo "verify: LỖI  $*" >&2; failed=1; }

port=$(sed -n 's/^QUILLO_PORT=//p' "$conf" | tail -n 1)
registry=$(sed -n 's/^QUILLO_REGISTRY=//p' "$conf" | tail -n 1)
version=$(awk '{sub(/^\*/, "", $2)} $2 ~ /^quillo-[0-9]+\.[0-9]+\.[0-9]+\.tar$/ {sub(/^quillo-/, "", $2); sub(/\.tar$/, "", $2); print $2}' \
    "$bundle/SHA256SUMS")

body=$(curl -q -fsS --noproxy '*' -m 10 "http://127.0.0.1:$port/healthz" 2>&1)
if [ $? -ne 0 ]; then
    bad "/healthz trên cổng $port không trả 200: $body"
elif printf '%s' "$body" | grep -q "\"version\": *\"$version\""; then
    ok "/healthz 200, version $version"
else
    bad "/healthz trả $body, cần version $version"
fi

if ! docker info >/dev/null 2>&1; then
    bad "không gọi được Docker (user cần quyền docker hoặc chạy bằng sudo)"
else
    for service in $services; do
        id=$(docker ps -aq --filter "label=com.docker.compose.project=$project" \
            --filter "label=com.docker.compose.service=$service" | head -n 1)
        if [ -z "$id" ]; then
            bad "dịch vụ $service không có container"
            continue
        fi
        # .State.Status (không phải cột Status của `docker ps`): container đang Restarting vẫn hiện trong `docker ps`.
        line=$(docker inspect -f '{{.Config.Image}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' "$id")
        set -- $line
        image=$1 state=$2 health=$3
        if [ "$state" != running ]; then
            bad "dịch vụ $service đang $state, không phải running"
        elif [ "$health" = unhealthy ]; then
            bad "dịch vụ $service unhealthy"
        elif [ -n "$registry" ] && [ "${image#"$registry"/}" = "$image" ]; then
            bad "dịch vụ $service chạy image $image, không phải từ registry nội bộ $registry"
        else
            ok "dịch vụ $service: $image ($state, health $health)"
        fi
    done
fi

exit "$failed"
