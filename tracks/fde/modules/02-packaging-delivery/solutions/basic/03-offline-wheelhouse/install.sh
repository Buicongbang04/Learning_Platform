#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
dest=$HOME/intake
python=/usr/bin/python3

(cd "$here" && sha256sum --quiet -c SHA256SUMS)

pip_wheel=$(ls "$here"/wheels/pip-*.whl)
app_wheel=$(ls "$here"/wheels/intake-*.whl)

releases=$HOME/.intake-releases
new=$releases/$(date +%Y%m%d%H%M%S)-$$
mkdir -p "$releases"
trap 'rm -rf -- "$new"' EXIT

"$python" -m venv --without-pip "$new"
pip() {
    "$new/bin/python" "$pip_wheel/pip" "$@" --quiet --no-index --disable-pip-version-check
}
pip install --find-links "$here/wheels" --require-hashes -r "$here/requirements.txt"
pip install --no-deps "$app_wheel"
"$new/bin/python" -c "import intake.cli, pydantic_core, yaml"

old=$(readlink "$dest" 2>/dev/null || true)
before=""
if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    before=$dest.before-$$
    mv -T "$dest" "$before"
fi
ln -sfn "$new" "$dest.link-$$"
mv -T "$dest.link-$$" "$dest"
trap - EXIT
case "$old" in
    "$releases"/*) [ "$old" != "$new" ] && rm -rf -- "$old" ;;
esac
if [ -n "$before" ]; then
    echo "Bản cài cũ không theo bố cục releases được giữ lại ở $before; kiểm tra rồi tự xoá" >&2
fi
echo "Đã cài intake vào $dest"
