#!/usr/bin/env bash
set -uo pipefail

usage() {
  echo "Usage: $0 [-n lần_thử] [-d giây_đầu] [-m giây_tối_đa] [-r mã,mã] [-j] [--] lệnh [tham số...]" >&2
  exit 64
}

attempts=5
base=1
max_delay=30
codes="6,7,28,75"
jitter=0
sleep_cmd="${RETRY_SLEEP_CMD:-sleep}"

# TODO 1: đọc -n, -d, -m, -r, -j bằng getopts và kiểm giá trị; sau option phải còn ít nhất một từ là lệnh
# TODO 2: chạy lệnh với đúng các tham số gốc; thành công thì thoát 0
# TODO 3: mã thoát không nằm trong danh sách -r -> "retry: exit N is not retryable" ra stderr, thoát bằng đúng mã đó
# TODO 4: còn lượt -> chờ min(max_delay, base * 2^(k-1)) giây qua "$sleep_cmd" (với -j: số nguyên ngẫu nhiên
#         trong [0, mức đó]), in "retry: attempt k/n exited N; sleeping Ss"; hết lượt ->
#         "retry: giving up after n attempts (exit N)" và thoát bằng mã cuối

echo "attempts=$attempts base=$base max=$max_delay codes=$codes jitter=$jitter sleep=$sleep_cmd" >&2
usage
