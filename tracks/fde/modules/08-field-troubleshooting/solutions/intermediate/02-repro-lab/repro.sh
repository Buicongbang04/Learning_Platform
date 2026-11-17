#!/bin/sh
# Tái hiện lỗi đăng nhập SSO của bệnh viện trên máy lab: IdP HTTPS dùng chứng chỉ do CA nội bộ cấp (đúng tên máy),
# còn quillo không được cho biết CA đó (QUILLO_OIDC_CA_FILE trống) nên không dựng được chuỗi tin cậy.
set -eu

quillo=/home/fde/quillo-1.0.0
lab=$HOME/repro-idp
host=sso.benhvien.local
port=8443

log() { printf 'repro: %s\n' "$*"; }

mkdir -p "$lab"
cd "$lab"
if [ ! -s leaf.pem ] || [ ! -s ca.pem ]; then
    log "tạo CA nội bộ giả và chứng chỉ cho $host"
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 30 \
        -subj "/O=Repro Lab/CN=Repro Internal Root CA" -keyout ca.key -out ca.pem 2>/dev/null
    openssl req -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -subj "/CN=$host" \
        -keyout leaf.key -out leaf.csr 2>/dev/null
    printf 'subjectAltName=DNS:%s\nbasicConstraints=CA:FALSE\n' "$host" >ext.cnf
    openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -CAcreateserial -days 30 -extfile ext.cnf \
        -out leaf.pem 2>/dev/null
fi

if [ -s s_server.pid ] && kill -0 "$(cat s_server.pid)" 2>/dev/null; then
    kill "$(cat s_server.pid)"
    sleep 1
fi
log "IdP giả nghe :$port (chỉ cần bắt tay TLS, lỗi xảy ra trước HTTP)"
nohup openssl s_server -quiet -accept "$port" -cert leaf.pem -key leaf.key -www >s_server.log 2>&1 &
echo $! >s_server.pid

cd "$quillo"
cat >compose.repro.yaml <<YAML
services:
  api:
    extra_hosts:
      - "$host:host-gateway"
YAML
sed -i -e '/^QUILLO_OIDC_ISSUER=/d' -e '/^QUILLO_OIDC_CLIENT_ID=/d' -e '/^QUILLO_OIDC_CA_FILE=/d' .env
printf '%s\n' "QUILLO_OIDC_ISSUER=https://$host:$port/realms/benhvien" "QUILLO_OIDC_CLIENT_ID=quillo" >>.env
sudo -n install -d -o 10001 -g 10001 -m 0700 oidc
if ! sudo -n test -s oidc/client-secret; then
    sudo -n sh -c 'umask 077; od -An -N24 -tx1 /dev/urandom | tr -d " \n" >oidc/client-secret; chown 10001:10001 oidc/client-secret; chmod 0400 oidc/client-secret'
fi
log "bật SSO như bệnh viện (compose.sso.yaml) và trỏ $host về máy lab"
docker compose -f compose.yaml -f compose.sso.yaml -f compose.repro.yaml up -d >/dev/null 2>&1

i=0
until curl -fsS --noproxy '*' -o /dev/null -m 5 http://127.0.0.1:18080/healthz; do
    i=$((i + 1))
    [ "$i" -lt 60 ] || { log "quillo không lên sau khi bật SSO"; docker compose ps; exit 1; }
    sleep 2
done
code=$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -m 30 http://127.0.0.1:18080/oidc/login)
log "/oidc/login trả $code"
docker compose logs --no-color --tail 5 api | grep 'IdP lỗi' | tail -n 1
