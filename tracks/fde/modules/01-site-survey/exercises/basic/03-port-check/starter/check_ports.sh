#!/bin/sh
set -u

if [ "$#" -eq 0 ]; then
    echo "Cách dùng: sh check_ports.sh <cổng> [<cổng> ...]" >&2
    exit 2
fi

# TODO 1: lấy danh sách socket TCP đang LISTEN (mọi địa chỉ, IPv4 và IPv6) mà không cần root
# TODO 2: với mỗi cổng theo đúng thứ tự tham số, in "<cổng> free" hoặc "<cổng> busy <tiến trình>"
# TODO 3: không thấy được tiến trình giữ cổng thì in "unknown" thay cho tên tiến trình

echo "check_ports.sh: chưa viết" >&2
exit 1
