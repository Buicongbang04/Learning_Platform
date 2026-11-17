#!/bin/sh
set -eu

: "${SSH:?đặt SSH là lệnh ssh tới máy khách}"
: "${BUNDLE:?đặt BUNDLE là đường dẫn quillo-1.1.0.tar trên laptop}"
: "${WORK:?đặt WORK là thư mục làm việc ghi được trên laptop}"

NEW=1.1.0
INSTALL=/home/fde/quillo-1.0.0
ROOT=quillo-$NEW
MIN_FREE_PCT=15

log() {
    printf '%s upgrade: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2
}

die() {
    log "DỪNG: $*"
    exit 1
}

remote() {
    $SSH "$1"
}

member_sha() {
    tar -xOf "$BUNDLE" "$ROOT/$1" | sha256sum | cut -d' ' -f1
}

manifest_sha() {
    python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["files"][sys.argv[2]])' "$WORK/manifest.json" "$1"
}

verified() {
    want=$(manifest_sha "$1")
    got=$(member_sha "$1")
    [ "$want" = "$got" ] || die "$1 trong bundle sai sha256 (manifest $want, thực tế $got)"
}

wait_version() {
    remote "i=0; until curl -fsS --noproxy '*' -m 5 http://127.0.0.1:18080/healthz 2>/dev/null | grep -q '\"version\":\"$1\"'; do
        i=\$((i + 1)); [ \$i -lt 75 ] || exit 1; sleep 2; done" || die "quillo không lên bản $1 sau 150 s"
}

mkdir -p "$WORK"
tar -xOf "$BUNDLE" "$ROOT/manifest.json" > "$WORK/manifest.json" || die "không đọc được manifest trong $BUNDLE"
version=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["version"])' "$WORK/manifest.json")
[ "$version" = "$NEW" ] || die "bundle là bản $version, cần $NEW"

remote "test -f $INSTALL/compose.yaml && test -f $INSTALL/.env" || die "không thấy bản cài ở $INSTALL"
current=$(remote "sed -n 's/^QUILLO_VERSION=//p' $INSTALL/.env")
log "bản đang chạy: $current"
size=$(remote "df -B1 --output=size / | tail -n 1" | tr -d ' ')
min_free=$((size * MIN_FREE_PCT / 100))
avail=$(remote "df -B1 --output=avail / | tail -n 1" | tr -d ' ')
log "đĩa trống $avail byte, mức sàn $min_free byte"

if [ "$current" != "$NEW" ]; then
    remote "mkdir -p ~/backups && chmod 0700 ~/backups"
    dump=$(remote "cd $INSTALL && ops/backup.sh ~/backups") || die "backup lỗi; chưa đổi gì"
    log "đã backup $dump"
fi

for member in $(tar -tf "$BUNDLE" | sed -n "s|^$ROOT/images/\(.*\.tar\)$|\1|p"); do
    meta=$(tar -xOf "$BUNDLE" "$ROOT/images/$member" | tar -xOf - manifest.json \
        | python3 -c 'import json, sys
for m in json.load(sys.stdin):
    for t in m.get("RepoTags") or []:
        print("sha256:" + m["Config"].rsplit("/", 1)[1], t)')
    [ -n "$meta" ] || die "images/$member không ghi RepoTags"
    missing=$(printf '%s\n' "$meta" | while read -r id tag; do
        have=$(remote "docker image inspect --format '{{.Id}}' $tag 2>/dev/null" || true)
        [ "$have" = "$id" ] || echo "$tag"
    done)
    if [ -z "$missing" ]; then
        log "images/$member: image đã có trên máy (cùng ID), không chép"
        continue
    fi
    verified "images/$member"
    bytes=$(tar -tvf "$BUNDLE" "$ROOT/images/$member" | awk '{print $3}')
    avail=$(remote "df -B1 --output=avail / | tail -n 1" | tr -d ' ')
    [ $((avail - 2 * bytes)) -ge "$min_free" ] || die "không đủ chỗ nạp images/$member ($bytes byte) mà vẫn giữ mức sàn"
    log "nạp images/$member ($bytes byte) thẳng vào docker, không ghi tệp tạm"
    tar -xOf "$BUNDLE" "$ROOT/images/$member" | $SSH "docker load" >&2 || die "docker load images/$member lỗi"
done

remote "mkdir -p $INSTALL/.release-$current && cd $INSTALL && for f in compose.yaml compose.sso.yaml \
    compose.extensions.yaml .env.example manifest.json REQUIREMENTS.yaml; do
        [ -e .release-$current/\$f ] || cp -p \$f .release-$current/\$f; done && cp -p .env .release-$current/env" \
    || die "không giữ được cấu hình bản $current"

for f in compose.yaml compose.sso.yaml compose.extensions.yaml .env.example REQUIREMENTS.yaml \
    migrations/0001_init.sql migrations/0002_v1_1_tags.sql ops/backup.sh ops/restore.sh ops/models_image.py; do
    verified "$f"
    tar -xOf "$BUNDLE" "$ROOT/$f" | $SSH "mkdir -p $INSTALL/$(dirname "$f") && cat > $INSTALL/$f.new && mv $INSTALL/$f.new $INSTALL/$f"
done
remote "cd $INSTALL && chmod 0755 ops/backup.sh ops/restore.sh"
$SSH "cat > $INSTALL/manifest.json" < "$WORK/manifest.json"

remote "cd $INSTALL && sed -i 's/^QUILLO_VERSION=.*/QUILLO_VERSION=$NEW/' .env && docker compose up -d" >&2 \
    || die "docker compose up với $NEW lỗi; chạy rollback.sh"
wait_version "$NEW"
log "quillo $NEW đã lên"
