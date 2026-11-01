#!/usr/bin/env bash
dest="${OLIST_BACKUP_DIR:-backups}"
keep=5
while getopts "k:d:" opt; do
  case "$opt" in
    k) keep="$OPTARG" ;;
    d) dest="$OPTARG" ;;
    *) ;;
  esac
done
stamp="${BACKUP_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$dest/$stamp"
pg_dump -Fc -f "$dest/$stamp/olist.dump"
(cd "$dest/$stamp" && sha256sum olist.dump > SHA256SUMS)
echo "created $dest/$stamp"
cd "$dest" && ls -1 | sort -r | tail -n +$((keep + 1)) | xargs -r rm -rf
