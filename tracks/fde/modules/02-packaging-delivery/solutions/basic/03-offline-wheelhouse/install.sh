#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
dest=$HOME/intake
python=/usr/bin/python3

(cd "$here" && sha256sum --quiet -c SHA256SUMS)

pip_wheel=$(ls "$here"/wheels/pip-*.whl)
app_wheel=$(ls "$here"/wheels/intake-*.whl)

rm -rf "$dest"
"$python" -m venv --without-pip "$dest"
pip() {
    "$dest/bin/python" "$pip_wheel/pip" "$@" --quiet --no-index --disable-pip-version-check
}
pip install --find-links "$here/wheels" --require-hashes -r "$here/requirements.txt"
pip install --no-deps "$app_wheel"

"$dest/bin/python" -c "import intake.cli, pydantic_core, yaml"
echo "Đã cài intake vào $dest"
