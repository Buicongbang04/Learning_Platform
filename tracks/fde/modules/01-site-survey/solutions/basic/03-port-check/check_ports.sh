#!/bin/sh
set -u
LC_ALL=C
export LC_ALL

if [ "$#" -eq 0 ]; then
    echo "Cách dùng: sh check_ports.sh <cổng> [<cổng> ...]" >&2
    exit 2
fi

listeners=$(ss -H -t -l -n -p 2>/dev/null)

for port in "$@"; do
    lines=$(printf '%s\n' "$listeners" | awk -v p="$port" '{ n = split($4, a, ":"); if (a[n] == p) print }')
    if [ -z "$lines" ]; then
        printf '%s free\n' "$port"
        continue
    fi
    owner=$(printf '%s\n' "$lines" | sed -n 's/.*users:(("\([^"]*\)".*/\1/p' | head -n 1)
    printf '%s busy %s\n' "$port" "${owner:-unknown}"
done
