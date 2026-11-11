#!/bin/sh
set -eu
here=$(cd "$(dirname "$0")" && pwd)
version=1.0.0
registry=10.0.2.101:5000
bundle=$HOME/quillo-$version
work=${TMPDIR:-/var/tmp}/quillo-deploy-$$
trap 'rm -rf "$work"' EXIT

log() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }

if [ ! -f "$bundle/manifest.json" ]; then
    log "giải nén $HOME/quillo-$version.tar"
    tar -xf "$HOME/quillo-$version.tar" -C "$HOME"
fi
mkdir -p "$work"
log "dựng image quillo-models:$version từ bundle"
python3 "$bundle/ops/models_image.py" "$bundle" "$work/quillo-models.tar"
log "đẩy image lên $registry"
python3 "$here/push_images.py" "$registry" "$bundle"/images/*.tar "$work/quillo-models.tar"
rm -f "$work/quillo-models.tar"

log "helm upgrade --install quillo"
if ! helm upgrade --install quillo "$bundle/chart/quillo-$version.tgz" -n quillo -f "$here/values.yaml" \
        --wait --timeout 150s; then
    kubectl -n quillo get pods -o wide >&2
    kubectl -n quillo get events --sort-by=.lastTimestamp | tail -20 >&2
    exit 1
fi
kubectl -n quillo get pods
