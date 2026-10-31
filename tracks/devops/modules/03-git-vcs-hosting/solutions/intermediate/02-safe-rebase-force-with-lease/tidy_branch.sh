#!/usr/bin/env bash
set -euo pipefail

remote=origin
base=main

refuse() {
  echo "refuse: $*" >&2
  exit 2
}

[[ $# -eq 0 ]] || refuse "Usage: $0 (không nhận tham số, chạy trên nhánh feature cần dọn)"

branch=$(git symbolic-ref --quiet --short HEAD) || refuse "HEAD đang detached, hãy checkout nhánh cần dọn"
case $branch in
  main | master | release/*) refuse "không viết lại lịch sử nhánh dùng chung: $branch" ;;
esac

git update-index -q --refresh >/dev/null || true
if ! git diff --quiet || ! git diff --cached --quiet; then
  refuse "working tree hoặc index chưa sạch, commit hoặc stash trước"
fi

lease=$(git rev-parse --verify --quiet "refs/remotes/$remote/$branch" || true)

git fetch --quiet "$remote" "+refs/heads/$base:refs/remotes/$remote/$base"

if ! GIT_SEQUENCE_EDITOR=true git rebase --quiet --interactive --autosquash "$remote/$base" >&2; then
  git rebase --abort >/dev/null 2>&1 || true
  echo "error: rebase lên $remote/$base bị xung đột, đã abort; rebase tay rồi chạy lại" >&2
  exit 1
fi

if ! git push --quiet --force-with-lease="refs/heads/$branch:$lease" "$remote" "HEAD:refs/heads/$branch" >&2; then
  echo "error: remote $branch đã khác ${lease:-<chưa có>} mà bạn thấy lần cuối; có người vừa push. Không ghi đè." >&2
  echo "Xem: git fetch $remote && git log HEAD..$remote/$branch" >&2
  exit 1
fi

echo "pushed $branch $(git rev-parse HEAD)"
