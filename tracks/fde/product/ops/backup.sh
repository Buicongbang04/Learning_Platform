#!/bin/sh
set -eu
umask 077

usage() {
    cat <<'TXT'
Dùng: backup.sh [--compose | --kubectl | --exec "LỆNH"] [-n NAMESPACE] <thư mục đích>

Sao lưu database quillo bằng pg_dump định dạng custom (-Fc) chạy BÊN TRONG container db, ghi
<đích>/quillo-<UTC>.dump và <đích>/quillo-<UTC>.dump.sha256. Từ chối khi đĩa trống ở <đích> nhỏ hơn
2 lần kích thước database ước tính (pg_database_size). Bản dump chứa mọi tài liệu của khách: tệp ghi mode 0600,
thư mục đích chmod 0700.

  --compose        (mặc định) "docker compose exec -T db", chạy trong thư mục cài đặt (chứa compose.yaml).
                   Podman hoặc binary compose khác: đặt COMPOSE, vd. COMPOSE="podman compose" hoặc COMPOSE=docker-compose
  --kubectl        "kubectl exec -i -n <NAMESPACE> <QUILLO_DB_TARGET> --" (mặc định quillo, statefulset/quillo-db)
  --exec "LỆNH"    tiền tố tuỳ ý chạy một lệnh trong container db, nhận stdin (vd. "podman exec -i quillo-db-1")

Biến: QUILLO_DB_USER, QUILLO_DB_NAME (mặc định quillo).
TXT
}

mode=compose
prefix=
namespace=${QUILLO_NAMESPACE:-quillo}
dest=
while [ $# -gt 0 ]; do
    case $1 in
        --compose) mode=compose ;;
        --kubectl) mode=kubectl ;;
        --exec) [ $# -ge 2 ] || { usage >&2; exit 2; }; mode=exec; prefix=$2; shift ;;
        -n|--namespace) [ $# -ge 2 ] || { usage >&2; exit 2; }; namespace=$2; shift ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "backup: tuỳ chọn lạ $1" >&2; usage >&2; exit 2 ;;
        *) [ -z "$dest" ] || { usage >&2; exit 2; }; dest=$1 ;;
    esac
    shift
done
[ -n "$dest" ] || { usage >&2; exit 2; }

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
    echo "backup: $*" >&2
    exit 1
}

mkdir -p "$dest"
chmod 0700 "$dest"
size=$(in_db psql -X -q -At -U "$user" -d "$name" -c "SELECT pg_database_size(current_database())") \
    || die "không chạy được psql trong container db qua: $prefix"
case $size in ''|*[!0-9]*) die "kích thước database không đọc được: $size" ;; esac
free_kb=$(df -Pk "$dest" | awk 'NR == 2 {print $4}')
case $free_kb in ''|*[!0-9]*) die "không đọc được dung lượng trống của $dest" ;; esac
need_kb=$(( size * 2 / 1024 + 1 ))
if [ "$free_kb" -lt "$need_kb" ]; then
    die "đĩa trống ở $dest còn ${free_kb} KiB, cần ít nhất ${need_kb} KiB (2 x database ${size} byte); dọn chỗ hoặc chọn đích khác"
fi

stamp=$(date -u +%Y%m%dT%H%M%SZ)
file="$dest/quillo-$stamp.dump"
part="$file.part"
trap 'rm -f "$part"' EXIT
trap 'rm -f "$part"; exit 130' INT TERM
in_db pg_dump -U "$user" -d "$name" -Fc --no-owner > "$part" || die "pg_dump lỗi"
in_db pg_restore --list < "$part" > /dev/null || die "bản dump vừa tạo không đọc lại được (pg_restore --list)"
mv "$part" "$file"
trap - EXIT INT TERM
(cd "$dest" && sha256sum "quillo-$stamp.dump" > "quillo-$stamp.dump.sha256")
echo "backup: database $name ($size byte) -> $file" >&2
echo "$file"
