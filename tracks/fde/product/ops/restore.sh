#!/bin/sh
set -eu

usage() {
    cat <<'TXT'
Dùng: restore.sh [--force] [--compose | --kubectl | --exec "LỆNH"] [-n NAMESPACE] <tệp .dump>

Khôi phục bản sao lưu của backup.sh vào database quillo bằng pg_restore chạy BÊN TRONG container db
(--clean --if-exists --single-transaction: lỗi giữa chừng thì database giữ nguyên như trước).
Kiểm sha256 theo <tệp>.sha256 trước khi chạm vào database. Từ chối khi database đang có tài liệu,
trừ khi có --force (ghi đè toàn bộ dữ liệu hiện có). Nên dừng api và worker trước khi restore.

  --compose        (mặc định) "docker compose exec -T db"; Podman: COMPOSE="podman compose"
  --kubectl        "kubectl exec -i -n <NAMESPACE> <QUILLO_DB_TARGET> --" (mặc định quillo, statefulset/quillo-db)
  --exec "LỆNH"    tiền tố tuỳ ý chạy một lệnh trong container db, nhận stdin

Biến: QUILLO_DB_USER, QUILLO_DB_NAME (mặc định quillo).
TXT
}

mode=compose
prefix=
namespace=${QUILLO_NAMESPACE:-quillo}
force=0
file=
while [ $# -gt 0 ]; do
    case $1 in
        --force) force=1 ;;
        --compose) mode=compose ;;
        --kubectl) mode=kubectl ;;
        --exec) [ $# -ge 2 ] || { usage >&2; exit 2; }; mode=exec; prefix=$2; shift ;;
        -n|--namespace) [ $# -ge 2 ] || { usage >&2; exit 2; }; namespace=$2; shift ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "restore: tuỳ chọn lạ $1" >&2; usage >&2; exit 2 ;;
        *) [ -z "$file" ] || { usage >&2; exit 2; }; file=$1 ;;
    esac
    shift
done
[ -n "$file" ] || { usage >&2; exit 2; }

user=${QUILLO_DB_USER:-quillo}
name=${QUILLO_DB_NAME:-quillo}
case $mode in
    compose) prefix="${COMPOSE:-docker compose} exec -T db" ;;
    kubectl) prefix="kubectl exec -i -n $namespace ${QUILLO_DB_TARGET:-statefulset/quillo-db} --" ;;
esac

in_db() {
    $prefix "$@"
}

die() {
    echo "restore: $*" >&2
    exit 1
}

[ -f "$file" ] || die "không có tệp $file"
[ -f "$file.sha256" ] || die "thiếu $file.sha256 (backup.sh ghi kèm); không restore tệp chưa kiểm được"
dir=$(dirname "$file")
base=$(basename "$file")
expected=$(awk 'NR == 1 {print $1}' "$file.sha256")
actual=$(cd "$dir" && sha256sum "$base" | awk '{print $1}')
[ -n "$expected" ] && [ "$expected" = "$actual" ] || die "sha256 của $base không khớp $base.sha256: tệp hỏng hoặc bị sửa"

count_documents() {
    exists=$(in_db psql -X -q -At -U "$user" -d "$name" -c "SELECT to_regclass('documents') IS NOT NULL") || return 1
    if [ "$exists" = t ]; then
        in_db psql -X -q -At -U "$user" -d "$name" -c "SELECT count(*) FROM documents"
    else
        echo 0
    fi
}

docs=$(count_documents) || die "không chạy được psql trong container db qua: $prefix"
case $docs in ''|*[!0-9]*) die "không đếm được tài liệu hiện có: $docs" ;; esac
if [ "$docs" -gt 0 ] && [ "$force" -ne 1 ]; then
    die "database $name đang có $docs tài liệu; restore sẽ ghi đè toàn bộ. Sao lưu bản hiện tại trước (backup.sh), rồi chạy lại với --force"
fi

in_db pg_restore -U "$user" -d "$name" --clean --if-exists --no-owner --single-transaction < "$file" \
    || die "pg_restore lỗi; database giữ nguyên như trước (single transaction)"
after=$(count_documents)
echo "restore: $base -> database $name ($after tài liệu; trước đó $docs)" >&2
