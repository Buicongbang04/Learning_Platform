#!/bin/sh
set -eu

: "${SSH:?đặt SSH là lệnh ssh tới máy khách}"
: "${BUNDLE:?đặt BUNDLE là đường dẫn quillo-1.1.0.tar trên laptop}"
: "${WORK:?đặt WORK là thư mục làm việc ghi được trên laptop}"

INSTALL=/home/fde/quillo-1.0.0
BACKUPS=/home/fde/backups
ROOT=quillo-1.1.0
MIN_FREE_PCT=15

log() {
    printf '%s pre-upgrade: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2
}

die() {
    log "DỪNG: $*"
    exit 1
}

remote() {
    $SSH "$1"
}

in_db() {
    remote "cd $INSTALL && docker compose exec -T db psql -X -q -At -U quillo -d $1 -c \"$2\""
}

mkdir -p "$WORK"
size=$(remote "df -B1 --output=size / | tail -n 1" | tr -d ' ')
free=$(remote "df -B1 --output=avail / | tail -n 1" | tr -d ' ')
floor=$((size * MIN_FREE_PCT / 100))
db_bytes=$(in_db quillo "SELECT pg_database_size(current_database())") || die "không đọc được kích thước database"
log "đĩa / trống $free byte (sàn $floor), database $db_bytes byte"
[ $((free - 2 * db_bytes)) -ge "$floor" ] || die "backup sẽ làm đĩa xuống dưới mức sàn; cần chỗ khác cho bản dump"

remote "mkdir -p $BACKUPS && chmod 0700 $BACKUPS"
dump=$(remote "cd $INSTALL && ops/backup.sh $BACKUPS") || die "ops/backup.sh lỗi"
dump_bytes=$(remote "stat -c %s $dump")
log "bản dump $dump ($dump_bytes byte)"

live=$(in_db quillo "SELECT (SELECT count(*) FROM documents) || ' ' || (SELECT count(*) FROM chunks)")
drop_drill() {
    in_db quillo "DROP DATABASE IF EXISTS restore_drill" >/dev/null 2>&1 || true
}
trap drop_drill EXIT
trap 'exit 130' INT TERM
drop_drill
in_db quillo "CREATE DATABASE restore_drill" >/dev/null
restored=$(remote "cd $INSTALL && docker compose exec -T db pg_restore -U quillo -d restore_drill --no-owner < $dump" \
    && in_db restore_drill "SELECT (SELECT count(*) FROM documents) || ' ' || (SELECT count(*) FROM chunks)") || restored=lỗi
drop_drill
trap - EXIT INT TERM
[ "$restored" = "$live" ] || die "restore thử ra '$restored', database đang chạy có '$live'"
log "restore thử khớp: tài liệu/chunk $live"

tar -xOf "$BUNDLE" "$ROOT/manifest.json" > "$WORK/manifest.json" || die "không đọc được manifest trong $BUNDLE"
remote "cat $INSTALL/manifest.json" > "$WORK/installed.json"
tar -tvf "$BUNDLE" > "$WORK/listing.txt"
: > "$WORK/images.txt"
for member in $(sed -n "s|.* $ROOT/\(images/[^/]*\.tar\)$|\1|p" "$WORK/listing.txt"); do
    config=$(tar -xOf "$BUNDLE" "$ROOT/$member" | tar -xOf - manifest.json \
        | python3 -c 'import json, sys; print(" ".join("sha256:" + m["Config"].rsplit("/", 1)[1] for m in json.load(sys.stdin)))')
    for id in $config; do
        if remote "docker image inspect $id >/dev/null 2>&1"; then
            echo "$member" >> "$WORK/images.txt"
        fi
    done
done

python3 - "$WORK" "$ROOT" "$free" "$db_bytes" "$dump" "$dump_bytes" "$floor" <<'PY'
import json
import sys
from pathlib import Path

work, root, free, db_bytes, dump, dump_bytes, floor = sys.argv[1:]
work = Path(work)
new = json.loads((work / "manifest.json").read_text())["files"]
installed = json.loads((work / "installed.json").read_text())["files"]
present = set((work / "images.txt").read_text().split())
sizes = {}
for line in (work / "listing.txt").read_text().splitlines():
    parts = line.split(None, 5)
    if len(parts) == 6 and parts[5].startswith(root + "/"):
        sizes[parts[5][len(root) + 1:]] = int(parts[2])
stage = sorted(path for path in new if not path.startswith("chart/") and installed.get(path) != new[path]
               and path not in present)
stage_bytes = sum(sizes[path] for path in stage)
plan = {"disk_free_bytes": int(free), "db_bytes": int(db_bytes), "dump": dump, "dump_bytes": int(dump_bytes),
        "stage": stage, "stage_bytes": stage_bytes,
        "free_after_bytes": int(free) - int(dump_bytes) - stage_bytes}
(work / "storage-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
if plan["free_after_bytes"] < int(floor):
    print(f"kế hoạch không vừa: còn {plan['free_after_bytes']} byte, sàn {floor}", file=sys.stderr)
    sys.exit(1)
print(json.dumps(plan, indent=2), file=sys.stderr)
PY
log "kế hoạch ghi ở $WORK/storage-plan.json"
