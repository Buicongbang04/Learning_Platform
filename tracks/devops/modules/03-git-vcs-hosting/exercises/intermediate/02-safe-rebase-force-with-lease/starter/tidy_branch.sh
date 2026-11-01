#!/usr/bin/env bash
set -euo pipefail

remote=origin
base=main

# TODO 1: không có tham số; đang ở nhánh (không detached), nhánh không phải main, master, release/*;
#         working tree và index sạch. Sai điều nào -> stderr, exit 2, không đổi gì
# TODO 2: ghi lại giá trị lease = refs/remotes/$remote/<nhánh> TRƯỚC mọi lệnh fetch (rỗng nếu chưa có)
# TODO 3: chỉ fetch $base, rồi rebase -i --autosquash lên $remote/$base không cần editor (GIT_SEQUENCE_EDITOR);
#         xung đột -> git rebase --abort, exit 1
# TODO 4: push --force-with-lease=<nhánh>:<lease> (không bao giờ --force trần); bị từ chối -> exit 1
# TODO 5: thành công -> dòng cuối stdout "pushed <nhánh> <sha HEAD>"

echo "remote=$remote base=$base" >&2
exit 1
