---
title: Tìm commit làm mất miễn phí ship bằng git bisect run
level: basic
services: []
files:
  - path: starter/check_free_shipping.sh
    note: 3 TODO, script kiểm cho git bisect run
  - path: starter/find_first_bad.sh
    note: 4 TODO, tự động hoá cả phiên bisect
  - path: tests/test_bisect.py
    note: Không sửa
  - path: tests/fixtures/build_shop_repo.py
    note: Dựng repo thử, chạy tay được
run:
  - uv run python tracks/devops/modules/03-git-vcs-hosting/exercises/basic/01-bisect-free-shipping/tests/fixtures/build_shop_repo.py /tmp/olist-bisect
  - uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/basic/01-bisect-free-shipping -q
---

## Mục tiêu

Dùng `git bisect run` để tìm commit gây lỗi trong vài chục commit mà không đọc từng diff, viết script kiểm phân biệt
được "bad" với "không kiểm được" (exit `125`), và gói cả phiên bisect thành một script luôn trả repo về trạng thái ban
đầu.

## Đề bài

Bug report từ team CS của Olist Shop: "đơn đúng 200,00 BRL giao tới SP bị tính phí ship, trong khi chính sách là miễn
phí từ 200 BRL". Bản `v1.0.0` đúng, `main` hiện tại sai. Giữa hai bản có vài chục commit, có đoạn code đang làm dở
không chạy được và có commit tạm xoá bảng giá.

Repo có package `olist_shop` với hàm `olist_shop.shipping.shipping_fee(subtotal, state)`. Dựng một bản để thử tay:

```bash
uv run python tracks/devops/modules/03-git-vcs-hosting/exercises/basic/01-bisect-free-shipping/tests/fixtures/build_shop_repo.py /tmp/olist-bisect
```

**1. `starter/check_free_shipping.sh`**: script cho `git bisect run`. Nó chạy với thư mục làm việc là gốc repo đã được
checkout tới commit cần kiểm, và gọi `shipping_fee(200, "SP")` bằng `python3` trên `PATH`.

| Tình huống ở commit đang kiểm | Exit |
| --- | --- |
| Phí bằng `0` | `0` (good) |
| Phí khác `0` | `1` (bad) |
| Không import được hoặc gọi hàm lỗi: `SyntaxError`, thiếu `rates.json`, mọi exception khác | `125` (skip) |

Script không được để lại tệp nào trong repo, kể cả tệp bị ignore: chạy Python với `-B` hoặc
`PYTHONDONTWRITEBYTECODE=1`. Test kiểm bằng `git status --porcelain --ignored` sau khi chạy. Lý do: bisect checkout
liên tục, và Python dùng lại `.pyc` cũ khi mtime (tính bằng giây) và kích thước tệp nguồn trùng nhau.

**2. `starter/find_first_bad.sh <good-ref> <bad-ref>`**: chạy trong gốc repo, tự động cả phiên:

1. `git bisect start <bad> <good>`. Lỗi (ref không tồn tại, good không phải tổ tiên của bad) thì exit `1`.
2. `git bisect run` với `check_free_shipping.sh` nằm **cùng thư mục với `find_first_bad.sh`**, gọi qua `bash` (tệp
   trong repo không có quyền thực thi). Bisect không kết luận được thì exit `1`.
3. Đọc commit lỗi đầu tiên từ `refs/bisect/bad`, in **dòng cuối của stdout** là `first-bad <sha đủ 40 ký tự>`. Output
   của git nên đưa sang stderr để stdout gọn.
4. Luôn chạy `git bisect reset` trước khi thoát, kể cả khi lỗi: repo phải về lại nhánh ban đầu (`main`), không còn
   `.git/BISECT_START`, `.git/BISECT_LOG`, working tree sạch.
5. Sai số tham số: exit `2`, `Usage:` ra stderr (đã có sẵn).

Test dựng repo bằng `tests/fixtures/build_shop_repo.py` với hai bố cục khác nhau (vị trí commit lỗi và đoạn hỏng khác
nhau), rồi:

- chạy `check_free_shipping.sh` ở 8 commit của bố cục A (good, bad, lỗi cú pháp, thiếu `rates.json`) và so exit code
  theo bảng trên;
- chạy `find_first_bad.sh v1.0.0 main` trên cả hai bố cục, so dòng `first-bad` với commit lỗi thật;
- chạy `find_first_bad.sh main v1.0.0` (đảo ngược) và đòi exit `1`, không in `first-bad`, repo về `main`.

Mọi lệnh có script của bạn (kể cả `git bisect run`) chạy trong sandbox bubblewrap của
[module 02](../../../../02-scripting/README.md#0-cài-đặt): `/` chỉ đọc, chỉ thư mục tạm của test ghi được, môi trường
biến dựng lại từ đầu với `HOME` tạm, `GIT_CONFIG_GLOBAL=/dev/null` và `GIT_CONFIG_SYSTEM=/dev/null`. Cấu hình Git của
bạn (`~/.gitconfig`, hooksPath, signing) không ảnh hưởng tới test, và test không đụng tới repo thật nào. Thiếu `bwrap`
thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/basic/01-bisect-free-shipping -q` pass toàn bộ, gồm
  `shellcheck -S style` sạch cho cả hai script.
- Giải thích được vì sao script kiểm trả `1` khi gặp `SyntaxError` sẽ làm bisect chỉ sai commit (test
  `test_naive_check_is_caught` chứng minh điều đó trên chính repo này).
- Nói được bisect cần khoảng bao nhiêu bước cho 48 commit, và vì sao lịch sử nhiều merge commit hoặc commit không build
  được làm bisect khó hơn.

## Gợi ý

### Gợi ý 1

Exit code của `git bisect run`: `0` good, `125` skip, `1`–`127` (trừ `125`) bad, `128` trở lên làm bisect dừng hẳn.
Vì vậy `python3 -c 'assert ...'` không đủ: Python thoát `1` cho cả `AssertionError` lẫn `SyntaxError`. Bắt exception
**trong** Python và tự chọn exit code: `python3 -B - <<'PY' ... PY` với `try/except Exception: sys.exit(125)`.

### Gợi ý 2

Đường dẫn của script kiểm: `here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)`. Dọn dẹp bằng
`trap 'git bisect reset >/dev/null 2>&1 || true' EXIT` đặt **trước** `git bisect start`. `git bisect reset` không có
option `--quiet`; nó nhận một tham số là commit để quay về, nên `git bisect reset -q` báo `'-q' is not a valid commit`
và repo vẫn kẹt ở trạng thái bisect.
