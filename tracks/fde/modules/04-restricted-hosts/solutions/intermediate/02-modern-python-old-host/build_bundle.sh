#!/bin/sh
set -eu

PBS_TAG=20261021
PBS_NAME=cpython-3.12.15+${PBS_TAG}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz
PBS_SHA256=6d7521138fd33afddc1ccd08abb007d9a2829e38117c2576f9efdc0ec73ce772
PIP=pip==25.1.1
TARGET_PYTHON=3.12
TARGET_ABI=cp312
TARGET_PLATFORMS="manylinux_2_31_x86_64 manylinux_2_28_x86_64 manylinux_2_17_x86_64 manylinux2014_x86_64"

die() { echo "build_bundle.sh: $*" >&2; exit 1; }

[ $# -eq 3 ] || { echo "Cách dùng: sh build_bundle.sh <thư mục app> <thư mục công cụ> <thư mục bundle>" >&2; exit 2; }
app=$(cd "$1" && pwd)
tools=$(cd "$2" && pwd)
out=$3
here=$(cd "$(dirname "$0")" && pwd)

pbs=$tools/python-build-standalone-$PBS_TAG/$PBS_NAME
[ -f "$pbs" ] || die "thiếu $pbs (tải theo phần 0. Cài đặt của README module 04)"
echo "$PBS_SHA256  $pbs" | sha256sum -c --quiet - || die "$pbs sai sha256"

rm -rf "$out"
mkdir -p "$out/wheels"
cp "$pbs" "$out/python.tar.gz"

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

cp "$here/install.sh" "$out/install.sh"
(cd "$out" && find . -type f ! -name SHA256SUMS | sort | xargs sha256sum > SHA256SUMS)
