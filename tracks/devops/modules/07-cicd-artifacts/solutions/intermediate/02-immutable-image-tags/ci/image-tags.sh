#!/usr/bin/env bash
set -euo pipefail

die() {
  echo "image-tags.sh: $2" >&2
  exit "$1"
}

ref="${GITHUB_REF:-}"
[[ -n "$ref" ]] || die 2 "thiếu GITHUB_REF"

sha="$(git rev-parse --verify HEAD)" || die 2 "không đọc được HEAD"
short="${sha:0:12}"

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  die 3 "working tree có thay đổi chưa commit; image phải build từ đúng một commit"
fi

slug() {
  local value
  value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  printf '%s' "${value:0:40}" | sed -E 's/-+$//'
}

semver='^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?$'

case "$ref" in
  refs/heads/main)
    stamp="$(TZ=UTC0 git show -s --format=%cd --date=format-local:%Y%m%d%H%M%S HEAD)"
    extra="main-${stamp}-${short}"
    ;;
  refs/heads/?*)
    name="$(slug "${ref#refs/heads/}")"
    [[ -n "$name" ]] || die 2 "tên nhánh không còn ký tự hợp lệ: ${ref}"
    extra="br-${name}-${short}"
    ;;
  refs/tags/?*)
    tag="${ref#refs/tags/}"
    [[ "$tag" =~ $semver ]] || die 4 "tag ${tag} không theo dạng vMAJOR.MINOR.PATCH[-pre]"
    target="$(git rev-parse --verify "refs/tags/${tag}^{commit}" 2>/dev/null)" || die 4 "không có tag ${tag} trong repo"
    [[ "$target" == "$sha" ]] || die 4 "tag ${tag} trỏ ${target:0:12}, không phải HEAD ${short}"
    extra="${tag#v}"
    ;;
  refs/pull/*/merge)
    number="${ref#refs/pull/}"
    number="${number%/merge}"
    [[ "$number" =~ ^[1-9][0-9]*$ ]] || die 2 "số PR không hợp lệ: ${ref}"
    extra="pr-${number}-${short}"
    ;;
  *)
    die 2 "không hỗ trợ ref ${ref}"
    ;;
esac

printf 'sha-%s\n%s\n' "$short" "$extra"
