#!/bin/bash
# cleanup_releases.sh: chạy bằng cron lúc 02:00 trên mọi máy app của Olist Shop.
# Giữ KEEP bản release mới nhất trong $DEPLOY_ROOT/releases, xoá phần còn lại,
# rồi dọn cache tạm trong $DEPLOY_ROOT/tmp.
# Cách dùng: cleanup_releases.sh /srv/olist-shop 3

DEPLOY_ROOT=$1
KEEP=${2:-3}

cd $DEPLOY_ROOT/releases

for r in $(ls -t | tail -n +$((KEEP+1))); do
  echo "removed $r"
  rm -rf $r
done

rm -rf $DEPLOY_ROOT/tmp/*

echo "done"
