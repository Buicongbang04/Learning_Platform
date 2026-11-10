#!/bin/sh
set -eu

die() { echo "build_bundle: $*" >&2; exit 1; }

[ $# -eq 2 ] || die "cách dùng: sh delivery/build_bundle.sh <site> <thư mục bundle>"
root=$(cd "$(dirname "$0")/.." && pwd)
site=$1
out=$2
conf=$root/sites/$site.conf

case $site in
    ""|*/*|.*) die "tên site không hợp lệ: '$site'" ;;
esac
[ -f "$conf" ] || die "không có sites/$site.conf; các site đang có: $(ls "$root/sites" | sed 's/\.conf$//' | tr '\n' ' ')"
case $out in
    ""|/|.|..) die "thư mục bundle không hợp lệ: '$out'" ;;
esac
if [ -e "$out" ] && [ -n "$(ls -A "$out")" ] && { [ ! -f "$out/SHA256SUMS" ] || [ ! -f "$out/install.sh" ]; }; then
    die "$out đã có tệp nhưng không phải bundle cũ (thiếu SHA256SUMS hoặc install.sh); không ghi đè"
fi

parent=$(dirname "$out")
mkdir -p "$parent"
stage=$(mktemp -d "$parent/.bundle.XXXXXX")
trap 'rm -rf "$stage"' EXIT

sh "$root/delivery/fetch_release.sh" "$stage"
version=$(sed -n 's/^QUILLO_VERSION=//p' "$root/delivery/release.lock")
sh "$root/delivery/fetch_compose.sh" "$stage/tools/docker-compose"
tar -xOf "$stage/quillo-$version.tar" "quillo-$version/REQUIREMENTS.yaml" > "$stage/REQUIREMENTS.yaml"
cp "$root/delivery/install.sh" "$stage/install.sh"
cp "$root/delivery/verify.sh" "$stage/verify.sh"
cp "$conf" "$stage/site.conf"
chmod 0644 "$stage/quillo-$version.tar" "$stage/REQUIREMENTS.yaml" "$stage/site.conf"
chmod 0755 "$stage" "$stage/tools" "$stage/tools/docker-compose" "$stage/install.sh" "$stage/verify.sh"
(
    cd "$stage"
    find . -type f ! -name SHA256SUMS ! -name SHA256SUMS.partial | sed 's#^\./##' | LC_ALL=C sort |
        while IFS= read -r file; do
            sha256sum "$file"
        done
) > "$stage/SHA256SUMS.partial"
mv "$stage/SHA256SUMS.partial" "$stage/SHA256SUMS"

rm -rf "$out"
mv "$stage" "$out"
trap - EXIT
echo "build_bundle: $out (site $site, quillo $version)"
echo "Gửi riêng cho IT khách (email/ticket), không để chung với bundle:"
echo "  sha256(SHA256SUMS) = $(sha256sum "$out/SHA256SUMS" | cut -d' ' -f1)"
