#!/bin/sh
set -u

json_string() {
    if [ -n "$1" ]; then
        printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    else
        printf 'null'
    fi
}

# TODO 1: os_id, os_version, kernel_major, glibc
# TODO 2: cpus, mem_mb, disk_free_gb_max
# TODO 3: gpu, proxy_url
# TODO 4: sudo, selinux, runtime
# TODO 5: egress
# TODO 6: in một object JSON đúng 13 khoá ra stdout (json_string in chuỗi có ngoặc kép, hoặc null khi rỗng)

echo "site_survey.sh: chưa viết" >&2
exit 1
