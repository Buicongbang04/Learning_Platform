#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
docker build \
    --build-arg http_proxy --build-arg https_proxy --build-arg no_proxy \
    --build-arg HTTP_PROXY --build-arg HTTPS_PROXY --build-arg NO_PROXY \
    -t fetcher:1 "$here"
