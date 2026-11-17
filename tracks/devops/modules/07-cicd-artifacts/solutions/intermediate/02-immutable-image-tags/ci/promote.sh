#!/usr/bin/env bash
set -euo pipefail

die() {
  echo "promote.sh: $2" >&2
  exit "$1"
}

[[ $# -eq 4 ]] || die 2 "cách dùng: promote.sh <registry> <repository> <tag-nguồn> <tag-đích>"
registry="$1"
repository="$2"
source_tag="$3"
target_tag="$4"
tag_re='^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$'
[[ "$source_tag" =~ $tag_re && "$target_tag" =~ $tag_re ]] || die 2 "tag không hợp lệ"

accept="application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json"
accept+=",application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.docker.distribution.manifest.v2+json"
base="http://${registry}/v2/${repository}/manifests"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

digest_of() {
  curl -fsS --noproxy '*' -o /dev/null -I -H "Accept: ${accept}" -D "$work/head" "${base}/$1" 2>/dev/null || return 1
  tr -d '\r' < "$work/head" | awk 'tolower($1) == "docker-content-digest:" { print $2 }'
}

status="$(curl -sS --noproxy '*' -o "$work/manifest" -w '%{http_code}' -D "$work/headers" -H "Accept: ${accept}" \
  "${base}/${source_tag}")" || die 6 "không gọi được registry ${registry}"
[[ "$status" == "200" ]] || die 4 "không có ${repository}:${source_tag} trên registry (HTTP ${status})"
content_type="$(tr -d '\r' < "$work/headers" | awk 'tolower($1) == "content-type:" { print $2 }')"
source_digest="$(tr -d '\r' < "$work/headers" | awk 'tolower($1) == "docker-content-digest:" { print $2 }')"
[[ -n "$content_type" && "$source_digest" == sha256:* ]] || die 6 "registry không trả Content-Type hay digest của manifest"

if target_digest="$(digest_of "$target_tag")" && [[ -n "$target_digest" ]]; then
  [[ "$target_digest" == "$source_digest" ]] || die 5 "${target_tag} đã trỏ ${target_digest}; tag phát hành không được dời"
  echo "$source_digest"
  exit 0
fi

curl -fsS --noproxy '*' -o /dev/null -X PUT -H "Content-Type: ${content_type}" --data-binary "@$work/manifest" \
  "${base}/${target_tag}" || die 6 "registry từ chối PUT manifest cho ${target_tag}"
[[ "$(digest_of "$target_tag")" == "$source_digest" ]] || die 6 "${target_tag} không trỏ đúng ${source_digest} sau khi gắn"
echo "$source_digest"
