#!/bin/sh
set -eu

die() { echo "install.sh: $*" >&2; exit 1; }
log() { echo "install.sh: $*" >&2; }

bundle=${1:?cách dùng: sh install.sh <fieldsync-x.y.z.tar>}
prefix=$HOME/fieldsync

[ -r "$bundle" ] || die "không đọc được $bundle"
case $bundle in
    /*) ;;
    *) bundle=$PWD/$bundle ;;
esac

work=$(mktemp -d "$HOME/.fieldsync-stage.XXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT TERM
if findmnt -no OPTIONS --target "$work" 2>/dev/null | tr ',' '\n' | grep -qx noexec; then
    die "$work nằm trên filesystem noexec; đặt HOME/thư mục cài ở chỗ chạy được chương trình"
fi

log "giải nén $bundle vào $work"
tar -xf "$bundle" -C "$work"
src=$(find "$work" -mindepth 1 -maxdepth 1 -type d -name 'fieldsync-*' | head -n 1)
[ -n "$src" ] || die "bundle không có thư mục fieldsync-*"
[ -x "$src/bin/fieldsync" ] || die "bundle thiếu bin/fieldsync"

nofile=$(ulimit -n)
total=$(find "$src/assets" -type f | wc -l)
if [ "$nofile" = unlimited ] || [ "$total" -le $((nofile - 64)) ]; then
    log "lập chỉ mục $total tệp (ulimit -n $nofile, một đợt)"
    "$src/bin/fieldsync" build-index --assets "$src/assets" --out "$src/index.json"
else
    batch=$((nofile - 64))
    [ "$batch" -ge 16 ] || die "ulimit -n = $nofile quá thấp để lập chỉ mục; nhờ IT nâng giới hạn nofile cho $(id -un)"
    log "lập chỉ mục $total tệp theo đợt $batch tệp (ulimit -n $nofile)"
    "$src/bin/fieldsync" build-index --assets "$src/assets" --out "$src/index.json" --max-open "$batch"
fi

log "cài vào $prefix"
new=$work/install
mkdir "$new"
mv "$src/bin" "$src/assets" "$src/index.json" "$new/"
if [ -d "$prefix" ]; then
    mv "$prefix" "$work/previous"
fi
if ! mv "$new" "$prefix"; then
    [ ! -d "$work/previous" ] || mv "$work/previous" "$prefix"
    die "không đặt được $prefix, đã giữ bản cũ"
fi
log "xong: $("$prefix/bin/fieldsync" --version), $total tệp"
