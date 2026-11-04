#!/bin/sh
set -u

os_id=$(. /etc/os-release && echo "$ID")
os_version=$(. /etc/os-release && echo "$VERSION_ID")
echo "os=${os_id}-${os_version}"

echo "user=$(id -un)"

server=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
echo "docker=${server:-missing}"

if docker compose version >/dev/null 2>&1; then
    echo "compose=yes"
else
    echo "compose=no"
fi

probe=https://pypi.org/simple/
proxy=${HTTPS_PROXY:-${https_proxy:-}}
if curl -fsSI --noproxy '*' --max-time 8 -o /dev/null "$probe" 2>/dev/null; then
    echo "egress=open"
elif [ -n "$proxy" ] && curl -sSI --max-time 8 -o /dev/null --proxy "$proxy" http://pypi.org/simple/ 2>/dev/null; then
    echo "egress=proxy"
else
    echo "egress=none"
fi
