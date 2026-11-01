#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: make_chain.sh OUTDIR" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
out=$1

# TODO: exit 2 nếu "$out/root-ca.key" đã có, không ghi đè gì
# TODO: root CA tự ký -> intermediate CA (pathlen:0) -> cert server có SAN, đúng keyUsage/extendedKeyUsage
# TODO: fullchain.pem = server.crt + intermediate-ca.crt; khoá riêng quyền 600
echo "make_chain: chưa viết" >&2
exit 1
