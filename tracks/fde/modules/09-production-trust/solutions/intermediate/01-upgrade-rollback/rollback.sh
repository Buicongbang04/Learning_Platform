#!/bin/sh
set -eu

: "${SSH:?đặt SSH là lệnh ssh tới máy khách}"

OLD=1.0.0
INSTALL=/home/fde/quillo-1.0.0
ARCHIVE=/home/fde/quillo-$OLD.tar

log() {
    printf '%s rollback: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2
}

die() {
    log "DỪNG: $*"
    exit 1
}

remote() {
    $SSH "$1"
}

count() {
    remote "cd $INSTALL && docker compose exec -T db psql -X -q -At -U quillo -d quillo \
        -c 'SELECT count(*) FROM documents' -c 'SELECT count(*) FROM chunks'" | tr '\n' ' '
}

current=$(remote "sed -n 's/^QUILLO_VERSION=//p' $INSTALL/.env")
before=$(count) || die "không đếm được tài liệu trước rollback"
log "bản đang chạy: $current; tài liệu/chunk trước rollback: $before"

if ! remote "docker image inspect quillo-api:$OLD >/dev/null 2>&1"; then
    log "image quillo-api:$OLD không còn trên máy, nạp lại từ $ARCHIVE"
    remote "tar -xOf $ARCHIVE quillo-$OLD/images/quillo-api.tar | docker load" >&2 \
        || die "không nạp được quillo-api:$OLD từ $ARCHIVE"
fi

saved=$INSTALL/.release-$OLD
if remote "test -d $saved"; then
    remote "cd $INSTALL && for f in compose.yaml compose.sso.yaml compose.extensions.yaml .env.example manifest.json \
        REQUIREMENTS.yaml; do if [ -e $saved/\$f ]; then cp -p $saved/\$f \$f.old && mv \$f.old \$f; fi; done" \
        || die "không trả lại cấu hình bản $OLD"
fi

remote "cd $INSTALL && sed -i 's/^QUILLO_VERSION=.*/QUILLO_VERSION=$OLD/' .env && docker compose up -d" >&2 \
    || die "docker compose up với $OLD lỗi"
remote "i=0; until curl -fsS --noproxy '*' -m 5 http://127.0.0.1:18080/healthz 2>/dev/null | grep -q '\"version\":\"$OLD\"'; do
    i=\$((i + 1)); [ \$i -lt 75 ] || exit 1; sleep 2; done" || die "quillo không lên bản $OLD sau 150 s"
after=$(count) || die "không đếm được tài liệu sau rollback"
[ "$before" = "$after" ] || die "số tài liệu/chunk đổi sau rollback: $before -> $after"
log "quillo $OLD đã lên, dữ liệu giữ nguyên ($after); schema mới hơn được giữ, không restore backup"
