#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
context=$(mktemp -d)
trap 'rm -rf "$context"' EXIT
cp "$here/Dockerfile" "$here/requirements.txt" "$here/fetch.py" "$context/"
mkdir "$context/site-ca"
find /usr/local/share/ca-certificates -name '*.crt' -type f 2>/dev/null | while read -r crt; do
    openssl x509 -in "$crt" -noout 2>/dev/null || { echo "build: bỏ qua $crt (không phải PEM)" >&2; continue; }
    cp "$crt" "$context/site-ca/"
    echo "build: đưa CA của site vào image: $(openssl x509 -in "$crt" -noout -subject)"
done
docker build \
    --build-arg http_proxy --build-arg https_proxy --build-arg no_proxy \
    --build-arg HTTP_PROXY --build-arg HTTPS_PROXY --build-arg NO_PROXY \
    -t fetcher:1 "$context"
