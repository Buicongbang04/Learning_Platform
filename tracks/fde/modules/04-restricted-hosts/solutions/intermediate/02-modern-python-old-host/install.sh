#!/bin/sh
set -eu

die() { echo "install.sh: $*" >&2; exit 1; }
log() { echo "install.sh: $*" >&2; }

here=$(cd "$(dirname "$0")" && pwd)
base=$HOME/.local/opt/census
bin=$HOME/.local/bin

[ "$(id -u)" -ne 0 ] || die "cài bằng user sẽ chạy app, không phải root"
(cd "$here" && sha256sum --quiet --strict -c SHA256SUMS) || die "bundle hỏng hoặc bị sửa (SHA256SUMS không khớp)"
app_wheel=$(ls "$here"/wheels/census-*.whl 2>/dev/null | head -n 1)
[ -n "$app_wheel" ] || die "bundle thiếu wheel của census"
stamp=$(sha256sum "$here/SHA256SUMS" | cut -c1-12)

mkdir -p "$base/releases" "$bin"
new=$base/releases/$stamp
if [ ! -f "$new/.complete" ]; then
    rm -rf -- "$new"
    mkdir -p "$new"
    trap 'rm -rf -- "$new"' EXIT
    trap 'exit 130' INT TERM
    log "giải nén Python 3.12 mang theo vào $new/python"
    tar -xzf "$here/python.tar.gz" -C "$new"
    "$new/python/bin/python3" -V >&2
    log "tạo môi trường và cài từ wheelhouse (không mạng)"
    "$new/python/bin/python3" -m venv "$new/venv"
    pip() {
        "$new/venv/bin/python" -m pip install --quiet --no-index --disable-pip-version-check "$@"
    }
    pip --find-links "$here/wheels" --require-hashes -r "$here/requirements.txt"
    pip --no-deps "$app_wheel"
    "$new/venv/bin/python" -c "import census.cli, pydantic_core" || die "app không import được sau khi cài"
    touch "$new/.complete"
    trap - EXIT
fi

ln -sfn "$new" "$base/current.new"
mv -T "$base/current.new" "$base/current"
ln -sfn "$base/current/venv/bin/census" "$bin/census.new"
mv -T "$bin/census.new" "$bin/census"
for old in "$base"/releases/*; do
    [ "$old" = "$new" ] || rm -rf -- "$old"
done
log "xong: $bin/census -> $new"
