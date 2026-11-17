#!/usr/bin/env bash
set -euo pipefail
umask 077

backup_dir="${ETCD_BACKUP_DIR:-/var/backups/etcd}"
keep="${ETCD_BACKUP_KEEP:-7}"
pki="${ETCD_PKI:-/etc/kubernetes/pki/etcd}"

case "$keep" in
  ''|*[!0-9]*|0) echo "ETCD_BACKUP_KEEP phải là số nguyên dương, đang là '$keep'" >&2; exit 2 ;;
esac

mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
snapshot="$backup_dir/etcd-snapshot-$(date -u +%Y%m%dT%H%M%SZ).db"

cleanup() {
  rm -f "$snapshot" "$snapshot.part"
}
trap cleanup ERR

etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert="$pki/ca.crt" \
  --cert="$pki/server.crt" \
  --key="$pki/server.key" \
  snapshot save "$snapshot"

status="$(etcdutl snapshot status "$snapshot" -w json)"
total_keys="$(printf '%s' "$status" | sed -n 's/.*"totalKey":[[:space:]]*\([0-9]*\).*/\1/p')"
if [ -z "$total_keys" ] || [ "$total_keys" -eq 0 ]; then
  echo "Snapshot $snapshot không có key nào, bỏ: $status" >&2
  rm -f "$snapshot"
  exit 1
fi
chmod 600 "$snapshot"
trap - ERR

find "$backup_dir" -maxdepth 1 -type f -name 'etcd-snapshot-*.db' -printf '%f\n' \
  | sort -r \
  | tail -n +"$((keep + 1))" \
  | while IFS= read -r old; do rm -f "$backup_dir/$old"; done

echo "$snapshot"
