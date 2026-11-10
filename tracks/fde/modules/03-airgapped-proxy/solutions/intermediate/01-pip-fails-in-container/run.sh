#!/bin/sh
set -eu

[ $# -eq 1 ] || { echo "Cách dùng: sh run.sh <url>" >&2; exit 2; }
docker run --rm \
    -e http_proxy -e https_proxy -e no_proxy -e HTTP_PROXY -e HTTPS_PROXY -e NO_PROXY \
    fetcher:1 "$1"
