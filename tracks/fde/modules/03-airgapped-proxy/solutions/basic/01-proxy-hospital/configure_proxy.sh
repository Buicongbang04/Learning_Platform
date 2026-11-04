#!/bin/sh
set -eu

usage() { echo "Cách dùng: sudo sh configure_proxy.sh <proxy url> <ca.pem>" >&2; exit 2; }
die() { echo "configure_proxy: $*" >&2; exit 1; }
say() { echo "configure_proxy: $*"; }

[ $# -eq 2 ] || usage
proxy=$1
ca=$2
no_proxy_list="localhost,127.0.0.1,::1,10.0.2.15,.benhvien.internal"
ca_name=benhvien-proxy-ca.crt

[ "$(id -u)" -eq 0 ] || die "cần chạy bằng root (sudo)"
case $proxy in
    http://*:[0-9]*) ;;
    *) die "proxy phải dạng http://host:port, nhận '$proxy'" ;;
esac
case $proxy in
    *@*) die "không ghi mật khẩu proxy vào cấu hình hệ thống; hỏi IT tài khoản dịch vụ hoặc proxy không cần xác thực" ;;
esac
[ -r "$ca" ] || die "không đọc được $ca"
openssl x509 -in "$ca" -noout 2>/dev/null || die "$ca không phải chứng chỉ PEM"
say "CA: $(openssl x509 -in "$ca" -noout -subject) $(openssl x509 -in "$ca" -noout -fingerprint -sha256)"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
changed_ca=0
changed_docker=0

put() {
    target=$1
    mode=$2
    if [ -f "$target" ] && cmp -s "$work/new" "$target"; then
        return 1
    fi
    install -D -m "$mode" "$work/new" "$target" || die "không ghi được $target"
    say "đã ghi $target"
    return 0
}

cp "$ca" "$work/new"
if put "/usr/local/share/ca-certificates/$ca_name" 0644 || [ ! -e "/etc/ssl/certs/${ca_name%.crt}.pem" ]; then
    update-ca-certificates >/dev/null || die "update-ca-certificates lỗi"
    changed_ca=1
fi

grep -Ev '^(http_proxy|https_proxy|no_proxy|HTTP_PROXY|HTTPS_PROXY|NO_PROXY)=' /etc/environment > "$work/new" || true
cat >> "$work/new" <<EOF
http_proxy="$proxy"
https_proxy="$proxy"
no_proxy="$no_proxy_list"
HTTP_PROXY="$proxy"
HTTPS_PROXY="$proxy"
NO_PROXY="$no_proxy_list"
EOF
put /etc/environment 0644 || true

cat > "$work/new" <<EOF
Acquire::http::Proxy "$proxy";
Acquire::https::Proxy "$proxy";
EOF
put /etc/apt/apt.conf.d/95benhvien-proxy 0644 || true

cat > "$work/new" <<EOF
[Service]
Environment="HTTP_PROXY=$proxy"
Environment="HTTPS_PROXY=$proxy"
Environment="NO_PROXY=$no_proxy_list"
EOF
if put /etc/systemd/system/docker.service.d/http-proxy.conf 0644; then
    changed_docker=1
fi

running_proxy() { docker info --format '{{.HTTPSProxy}}' 2>/dev/null || true; }
if [ "$changed_docker" -eq 1 ] || [ "$changed_ca" -eq 1 ] || [ "$(running_proxy)" != "$proxy" ]; then
    if [ "$(docker info --format '{{.LiveRestoreEnabled}}' 2>/dev/null || true)" != "true" ]; then
        echo "configure_proxy: CẢNH BÁO: live-restore tắt, restart Docker sẽ dừng rồi chạy lại MỌI container trên máy" >&2
    fi
    systemctl daemon-reload || die "systemctl daemon-reload lỗi"
    systemctl restart docker || die "restart docker lỗi; xem journalctl -u docker"
    say "đã restart docker"
fi

[ "$(running_proxy)" = "$proxy" ] || die "Docker daemon đang chạy chưa nhận proxy $proxy"
say "xong"
