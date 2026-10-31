---
title: Dọn nhánh bằng rebase --autosquash và push --force-with-lease không ghi đè đồng nghiệp
level: intermediate
services: []
files:
  - path: starter/tidy_branch.sh
    note: 5 TODO
  - path: tests/test_tidy.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/intermediate/02-safe-rebase-force-with-lease -q
---

## Mục tiêu

Viết lại lịch sử một nhánh đã push mà không bao giờ làm mất commit của người khác: gộp `fixup!` không cần editor,
rebase lên `main` mới nhất, abort sạch khi xung đột, và hiểu vì sao `--force-with-lease` không kèm giá trị vẫn có thể
ghi đè đồng nghiệp.

## Đề bài

Minh làm nhánh `feature/pix-payment` của Olist Shop, đã push để mở PR. Trong lúc review, Minh thêm các commit
`fixup! feat(payments): pix qr code` và `fixup! feat(payments): pix webhook` (tạo bằng `git commit --fixup=<sha>`).
Trước khi merge, team muốn nhánh gọn: mỗi thay đổi một commit, nằm trên `main` mới nhất. Đôi khi Hoa cũng push thẳng
lên nhánh này để sửa giúp.

Viết `starter/tidy_branch.sh`, không nhận tham số, chạy trong repo của Minh (remote tên `origin`, nhánh gốc `main`):

1. **Chặn trước khi đổi gì** (exit `2`, lý do ra stderr, không đổi nhánh, working tree hay remote):
   có tham số; `HEAD` detached; nhánh hiện tại là `main`, `master` hoặc bắt đầu bằng `release/`; working tree hoặc
   index có thay đổi chưa commit (tệp chưa track không tính).
2. **Ghi lại lease trước mọi lệnh fetch**: giá trị hiện tại của `refs/remotes/origin/<nhánh>`, tức thứ Minh thấy lần
   cuối trên remote. Nhánh chưa từng push thì lease rỗng.
3. **Chỉ fetch `main`** (`git fetch origin main` hoặc refspec tương đương), không fetch nhánh của chính mình.
4. **Rebase không cần editor**: `git rebase -i --autosquash origin/main` với `GIT_SEQUENCE_EDITOR` đặt sao cho danh
   sách todo được chấp nhận nguyên trạng. Mỗi `fixup!` gộp vào commit gốc, giữ thứ tự và message của commit gốc.
   Xung đột thì `git rebase --abort`, exit `1`: nhánh về đúng commit cũ, không còn trạng thái rebase dở.
5. **Push có điều kiện**: `git push --force-with-lease=<nhánh>:<lease> origin HEAD:<nhánh>`. Lease rỗng nghĩa là
   "nhánh chưa được có trên remote". Không bao giờ dùng `--force` hay `+refspec`. Remote đã khác lease (có người vừa
   push) thì push bị từ chối: exit `1`, giải thích ra stderr.
6. **Thành công**: exit `0`, dòng cuối stdout đúng dạng `pushed <nhánh> <sha 40 ký tự của HEAD>`.

Test dựng một remote bare `origin.git` trong thư mục tạm, một clone làm đồng nghiệp, và clone của Minh; không có mạng,
không có GitHub. Các ca: nhánh có hai `fixup!` và `main` đã có commit mới; Hoa đã push lên nhánh sau lần fetch cuối của
Minh (commit của Hoa phải còn nguyên trên remote); `main` sửa đúng dòng mà nhánh sửa (xung đột); nhánh chưa từng push;
đang ở `main`; `HEAD` detached; working tree bẩn.

Script chạy trong sandbox bubblewrap của [module 02](../../../../02-scripting/README.md#0-cài-đặt): chỉ thư mục tạm
của test ghi được, môi trường dựng lại từ đầu với `HOME` tạm, `GIT_CONFIG_GLOBAL=/dev/null`,
`GIT_CONFIG_SYSTEM=/dev/null`, `GIT_EDITOR=true`. Cấu hình Git của bạn (`pull.rebase`, `rebase.autoSquash`, signing,
credential helper) không ảnh hưởng, và không lệnh nào chạm tới remote thật. Thiếu `bwrap` thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/intermediate/02-safe-rebase-force-with-lease -q`
  pass toàn bộ, gồm `shellcheck -S style` sạch.
- Giải thích được vì sao `git fetch origin && git push --force-with-lease` vẫn ghi đè commit của Hoa (test
  `test_naive_lease_is_caught` chạy đúng script đó), và hai cách sửa: lease tường minh, hoặc thêm `--force-if-includes`.
- Nói được khi nào **không** rebase nhánh đã push (nhánh nhiều người cùng làm, nhánh release) và team nên chọn gì thay
  thế (merge `main` vào nhánh, squash khi merge PR).

## Gợi ý

### Gợi ý 1

`git symbolic-ref --quiet --short HEAD` trả tên nhánh, hoặc lỗi khi detached. `git diff --quiet && git diff --cached
--quiet` kiểm working tree và index. Lease: `git rev-parse --verify --quiet "refs/remotes/origin/$branch" || true`.

### Gợi ý 2

`GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash origin/main`: Git mở "editor" cho danh sách todo, `true` thoát
`0` mà không sửa gì, và danh sách đã được `--autosquash` sắp sẵn. Lease tường minh trên push:
`--force-with-lease="refs/heads/$branch:$lease"`. Bọc rebase và push trong `if ! ...; then ...; exit 1; fi` để
`set -e` không thoát trước khi kịp `rebase --abort`.
