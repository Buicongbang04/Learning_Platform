#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: make_chain.sh OUTDIR" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
out=$1

if [[ -e "$out/root-ca.key" ]]; then
  echo "make_chain: $out/root-ca.key đã có, không ghi đè CA" >&2
  exit 2
fi

mkdir -p "$out"
umask 077
work=$(mktemp -d "$out/.work.XXXXXX")
trap 'rm -rf "$work"' EXIT

cat >"$work/req.cnf" <<'CNF'
[req]
distinguished_name = dn
prompt = no
[dn]
CN = placeholder
CNF

cat >"$work/intermediate.ext" <<'CNF'
basicConstraints = critical, CA:TRUE, pathlen:0
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always
CNF

cat >"$work/server.ext" <<'CNF'
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = DNS:shop.olist.test, DNS:api.olist.test, IP:127.0.0.1
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always
CNF

newkey() {
  openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$1"
  chmod 600 "$1"
}

newkey "$work/root-ca.key"
openssl req -new -x509 -config "$work/req.cnf" -key "$work/root-ca.key" -sha256 -days 3650 \
  -subj "/O=Olist Shop Lab/CN=Olist Shop Lab Root CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash" \
  -out "$work/root-ca.crt"

newkey "$work/intermediate-ca.key"
openssl req -new -config "$work/req.cnf" -key "$work/intermediate-ca.key" \
  -subj "/O=Olist Shop Lab/CN=Olist Shop Lab Intermediate CA" -out "$work/intermediate-ca.csr"
openssl x509 -req -in "$work/intermediate-ca.csr" -CA "$work/root-ca.crt" -CAkey "$work/root-ca.key" \
  -set_serial "0x$(openssl rand -hex 16)" -sha256 -days 1825 -extfile "$work/intermediate.ext" \
  -out "$work/intermediate-ca.crt"

newkey "$work/server.key"
openssl req -new -config "$work/req.cnf" -key "$work/server.key" \
  -subj "/O=Olist Shop Lab/CN=shop.olist.test" -out "$work/server.csr"
openssl x509 -req -in "$work/server.csr" -CA "$work/intermediate-ca.crt" -CAkey "$work/intermediate-ca.key" \
  -set_serial "0x$(openssl rand -hex 16)" -sha256 -days 90 -extfile "$work/server.ext" \
  -out "$work/server.crt"

cat "$work/server.crt" "$work/intermediate-ca.crt" >"$work/fullchain.pem"
openssl verify -no-CApath -CAfile "$work/root-ca.crt" -untrusted "$work/intermediate-ca.crt" \
  -verify_hostname shop.olist.test "$work/server.crt" >/dev/null

for name in root-ca.key root-ca.crt intermediate-ca.key intermediate-ca.crt server.key server.crt fullchain.pem; do
  mv "$work/$name" "$out/$name"
done
chmod 644 "$out"/*.crt "$out/fullchain.pem"
