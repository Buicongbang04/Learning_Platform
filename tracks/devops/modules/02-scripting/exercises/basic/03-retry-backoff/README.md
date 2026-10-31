---
title: Bọc lệnh bằng retry có exponential backoff, chỉ thử lại lỗi tạm thời
level: basic
services: []
files:
  - path: starter/retry.sh
    note: 4 TODO
  - path: tests/test_retry.py
    note: Không sửa
run:
  - RETRY_SLEEP_CMD=echo bash tracks/devops/modules/02-scripting/exercises/basic/03-retry-backoff/starter/retry.sh -n 3 -- curl -sS --max-time 2 http://127.0.0.1:9/
  - uv run pytest tracks/devops/modules/02-scripting/exercises/basic/03-retry-backoff -q
---

## Mục tiêu

Viết một wrapper `retry` dùng chung cho mọi script vận hành (chờ Postgres lên trong `bootstrap.sh`, gọi API khi
deploy, tải artifact): thử lại có giới hạn, chờ tăng theo cấp số nhân có trần, tuỳ chọn jitter, và **chỉ** thử lại lỗi
tạm thời. Biết thêm một "seam" để test logic thời gian mà không phải ngủ thật.

## Đề bài

Viết `starter/retry.sh [-n lần_thử] [-d giây_đầu] [-m giây_tối_đa] [-r mã,mã] [-j] [--] lệnh [tham số...]`:

| Option | Mặc định | Nghĩa |
| --- | --- | --- |
| `-n` | `5` | Tổng số lần chạy lệnh, kể cả lần đầu. Số nguyên `>= 1` |
| `-d` | `1` | Thời gian chờ trước lần thử lại thứ nhất, giây. Số nguyên `>= 0` |
| `-m` | `30` | Trần thời gian chờ, giây. Số nguyên `>= 0` |
| `-r` | `6,7,28,75` | Danh sách exit code được coi là tạm thời, cách nhau bằng dấu phẩy, không có khoảng trắng |
| `-j` | tắt | Full jitter: mỗi lần chờ là số nguyên ngẫu nhiên trong `[0, mức backoff]` |

Mã mặc định: curl `6` (không phân giải được tên), `7` (không kết nối được), `28` (quá giờ), và `75` (`EX_TEMPFAIL`
trong `sysexits.h`, quy ước cho "thử lại sau"). Curl `22` (HTTP `>= 400` khi dùng `-f`) **không** nằm trong danh sách,
vì nó gộp cả `404`, `401` (thử lại vô ích) lẫn `503`.

Hành vi:

1. Chạy lệnh với **đúng** các tham số gốc (giữ dấu cách, chuỗi rỗng, `*`, tham số bắt đầu bằng `-`). stdout và stderr
   của lệnh đi thẳng ra ngoài.
2. Lệnh trả `0`: `retry.sh` thoát `0`, không in gì thêm.
3. Exit code không nằm trong danh sách `-r`: in ra stderr `retry: exit <mã> is not retryable` và thoát bằng đúng mã
   đó, không thử lại. Lệnh không tồn tại (`127`) rơi vào trường hợp này.
4. Exit code tạm thời và còn lượt: chờ rồi chạy lại. Mức backoff trước lần thử lại thứ `k` (k = 1, 2, ...) là
   `min(m, d * 2^(k-1))`. Trước khi chờ, in ra stderr đúng một dòng
   `retry: attempt <số lần đã chạy>/<n> exited <mã>; sleeping <giây>s`.
5. Exit code tạm thời và đã chạy đủ `n` lần: in `retry: giving up after <n> attempts (exit <mã>)` ra stderr, thoát
   bằng mã của lần chạy cuối.
6. Chờ bằng lệnh trong biến `RETRY_SLEEP_CMD` (mặc định `sleep`), gọi đúng một lần cho mỗi lần chờ với **một** tham
   số là số giây nguyên, kể cả khi số giây là `0`. Test đặt biến này thành một script ghi lại số giây thay vì ngủ.
7. Lỗi cách dùng (option lạ, giá trị không hợp lệ, không có lệnh sau option): stderr bắt đầu bằng `Usage:`, stdout
   rỗng, exit `64` (`EX_USAGE`). Không dùng `2` vì `retry.sh` phải trả lại exit code của lệnh được bọc, và `2` là mã
   rất nhiều lệnh dùng.

Ví dụ, lệnh trả `7`, `7`, rồi `0` với mặc định: chạy 3 lần, chờ `1` rồi `2` giây, stderr có hai dòng
`retry: attempt 1/5 exited 7; sleeping 1s` và `retry: attempt 2/5 exited 7; sleeping 2s`, exit `0`. Với
`-n 6 -d 2 -m 5` và lệnh luôn trả `28`: chờ `2 4 5 5 5`, exit `28`.

Test kiểm jitter bằng cách chạy ba lần với `-j -n 6`: mọi lần chờ nằm trong `[0, 1]`, `[0, 2]`, `[0, 4]`, `[0, 8]`,
`[0, 16]`, và ít nhất một lần trong ba lần chạy có dãy khác hẳn `1 2 4 8 16`.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/02-scripting/exercises/basic/03-retry-backoff -q` pass toàn bộ, gồm
  `shellcheck -S style` sạch.
- Giải thích được vì sao script này **không** dùng `set -e`, và vì sao retry không có jitter có thể làm sự cố tệ hơn
  (thundering herd).
- Nói được ba loại lỗi không bao giờ nên retry, và vì sao retry một thao tác không idempotent (POST tạo đơn hàng) là
  nguy hiểm.

## Gợi ý

### Gợi ý 1

Chạy lệnh bằng `"$@"` (có ngoặc kép) sau khi `shift $((OPTIND - 1))`. Kiểm mã thuộc danh sách bằng so chuỗi có
dấu phẩy bao hai đầu: `[[ ",$codes," == *",$rc,"* ]]`. Kiểm danh sách hợp lệ bằng `^[0-9]+(,[0-9]+)*$`.

### Gợi ý 2

Với `set -e`, `"$@"` trả lỗi là script chết ngay, nên dùng `set -uo pipefail` và tự lấy `rc=$?` ngay sau lệnh. Số
ngẫu nhiên trong `[0, x]`: `$((RANDOM % (x + 1)))`. Tính trần trước khi nhân đôi để biến không tràn khi `-n` lớn:
`delay=$((delay * 2 < max ? delay * 2 : max))`.
