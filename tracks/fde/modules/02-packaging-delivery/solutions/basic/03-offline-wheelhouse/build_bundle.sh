#!/bin/sh
set -eu

PIP=pip==25.1.1
TARGET_PYTHON=3.10
TARGET_ABI=cp310
TARGET_PLATFORMS="manylinux_2_35_x86_64 manylinux_2_34_x86_64 manylinux_2_28_x86_64 manylinux_2_17_x86_64 manylinux2014_x86_64 linux_x86_64"

[ $# -eq 2 ] || { echo "Cách dùng: sh build_bundle.sh <thư mục app> <thư mục bundle>" >&2; exit 2; }
app=$(cd "$1" && pwd)
out=$2
here=$(cd "$(dirname "$0")" && pwd)

rm -rf "$out"
mkdir -p "$out/wheels"

uv export --project "$app" --frozen --no-dev --no-emit-project --format requirements.txt \
    --output-file "$out/requirements.txt" >/dev/null
uv build --project "$app" --wheel --out-dir "$out/wheels" >/dev/null

platforms=""
for tag in $TARGET_PLATFORMS; do
    platforms="$platforms --platform $tag"
done
uvx --from "$PIP" pip download --quiet --dest "$out/wheels" --only-binary=:all: \
    --python-version "$TARGET_PYTHON" --implementation cp --abi "$TARGET_ABI" --abi abi3 --abi none $platforms \
    --require-hashes -r "$out/requirements.txt"
uvx --from "$PIP" pip download --quiet --dest "$out/wheels" --only-binary=:all: --no-deps "$PIP"

cp "$here/install.sh" "$out/install.sh"
(cd "$out" && find . -type f ! -name SHA256SUMS | sort | xargs sha256sum > SHA256SUMS)
