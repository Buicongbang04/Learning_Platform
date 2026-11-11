#!/bin/sh
set -eu
version=$1
cd "$HOME"
tar -xf "quillo-$version.tar"
rm -f "quillo-$version.tar"
cd "quillo-$version"
for archive in images/*.tar; do
    docker load -q -i "$archive"
done
rm -rf images
umask 077
token=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
password=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
sed -e "s/^QUILLO_VERSION=.*/QUILLO_VERSION=$version/" \
    -e "s/^QUILLO_ADMIN_TOKEN=.*/QUILLO_ADMIN_TOKEN=$token/" \
    -e "s/^QUILLO_DB_PASSWORD=.*/QUILLO_DB_PASSWORD=$password/" \
    -e "s/^QUILLO_BIND=.*/QUILLO_BIND=0.0.0.0/" .env.example > .env
umask 022
sudo -n install -d -o 10001 -g 10001 -m 0750 inbox
docker compose up -d
i=0
until curl -fsS --noproxy '*' -o /dev/null -m 5 http://127.0.0.1:18080/healthz; do
    i=$((i + 1))
    [ "$i" -lt 120 ] || { docker compose ps; docker compose logs --tail 30; exit 1; }
    sleep 2
done
