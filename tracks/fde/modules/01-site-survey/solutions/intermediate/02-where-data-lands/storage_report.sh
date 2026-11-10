#!/bin/sh
set -u
LC_ALL=C
export LC_ALL

json_or_null() {
    if [ -n "$1" ]; then
        printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    else
        printf 'null'
    fi
}

number_or_null() {
    if [ -n "$1" ]; then printf '%s' "$1"; else printf 'null'; fi
}

runtime=""
root=""
if command -v docker >/dev/null 2>&1 && root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null) && [ -n "$root" ]; then
    runtime=docker
elif command -v podman >/dev/null 2>&1 && root=$(podman info --format '{{.Store.GraphRoot}}' 2>/dev/null) && [ -n "$root" ]; then
    runtime=podman
else
    root=""
fi

mount=""
free_gb=""
inodes=""
if [ -n "$root" ]; then
    probe=$root
    while [ ! -e "$probe" ] && [ "$probe" != / ]; do
        probe=$(dirname "$probe")
    done
    mount=$(df -P -k "$probe" | awk 'NR==2 {print $6}')
    free_gb=$(df -P -k "$probe" | awk 'NR==2 {printf "%.2f", $4 / 1048576}')
    inodes=$(df -P -i "$probe" | awk 'NR==2 && $2 > 0 {printf "%d", 100 * $4 / $2}')
fi

printf '{\n'
printf '  "runtime": %s,\n' "$(json_or_null "$runtime")"
printf '  "data_root": %s,\n' "$(json_or_null "$root")"
printf '  "data_mount": %s,\n' "$(json_or_null "$mount")"
printf '  "data_free_gb": %s,\n' "$(number_or_null "$free_gb")"
printf '  "inodes_free_pct": %s\n' "$(number_or_null "$inodes")"
printf '}\n'
