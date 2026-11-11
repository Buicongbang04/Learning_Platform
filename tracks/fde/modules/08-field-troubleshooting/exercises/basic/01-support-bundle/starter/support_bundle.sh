#!/bin/sh
# Bản đồng nghiệp viết vội trong buổi gọi với khách. Chạy được, nhưng đừng gửi bundle này đi đâu.
out=$1
dir=/tmp/bundle
mkdir -p $dir
uname -a > $dir/uname.txt
df -h > $dir/df.txt
env > $dir/env.txt
systemctl show docbridge > $dir/docbridge-show.txt
cp /etc/docbridge/docbridge.conf $dir/
cp /var/log/docbridge/docbridge.log $dir/
docker inspect docbridge-cache > $dir/cache.json
tar -czf $out -C /tmp bundle
