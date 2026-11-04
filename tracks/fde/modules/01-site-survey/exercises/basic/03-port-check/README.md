---
title: Cổng nào đang bị chiếm (không cần root)
level: basic
services: []
files:
  - path: starter/check_ports.sh
    note: 3 TODO, POSIX sh
  - path: tests/test_check_ports.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/01-site-survey/exercises/basic/03-port-check -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

`quillo` cần cổng `18080` trống. Survey JSON không trả lời được câu đó, nên trước ngày cài bạn gửi khách một kiểm tra
cổng chạy được với user thường. Bài tập luyện đọc bảng socket của Linux và biết **giới hạn** của những gì user thường
nhìn thấy.

## Đề bài

Viết `starter/check_ports.sh`. Cách dùng: `sh check_ports.sh <cổng> [<cổng> ...]`. Với mỗi cổng, **theo đúng thứ tự tham
số**, in một dòng:

- `<cổng> free` nếu không có socket **TCP** nào đang `LISTEN` trên cổng đó (ở bất kỳ địa chỉ nào, IPv4 hay IPv6);
- `<cổng> busy <tiến trình>` nếu có, với `<tiến trình>` là tên tiến trình giữ socket (tên như `ss -p` hiển thị, vd.
  `python3`), hoặc `unknown` khi user chạy script **không thấy** được tiến trình đó.

Ràng buộc: POSIX `sh`, không gọi `sudo`, không in gì khác ra stdout, thoát `0` trong 10 giây. Socket UDP không tính (cổng
của sản phẩm là TCP). Cổng `8080` và `28080` là hai cổng khác nhau.

Test boot một VM `lab-open` (1024 MB), chọn ngẫu nhiên vài cổng rồi dựng: một HTTP server của chính user `fde` nghe ở
`127.0.0.1`, một HTTP server của **root** nghe ở `[::]`, một socket UDP, và để trống một cổng. Script được hỏi các cổng
đó (theo thứ tự xáo trộn) cùng cổng `22` và một cổng có đuôi trùng với một cổng đang bận. Sau đó test tắt server của
`fde` và chạy lại script.

## Tiêu chí đạt

- `test_ports_seen_without_root`: script thoát `0` trong ≤10 s, đúng một dòng mỗi cổng theo thứ tự, đúng dạng
  `<cổng> free` hoặc `<cổng> busy <tiến trình>`.
- Cổng của server user `fde` ⇒ `busy python3`; cổng của server root và cổng `22` ⇒ `busy unknown`.
- Cổng trống, cổng chỉ có UDP, cổng có đuôi trùng ⇒ `free`.
- Lần chạy thứ hai, sau khi server của `fde` tắt: cổng đó ⇒ `free`, các cổng khác giữ nguyên kết quả.

## Gợi ý

### Gợi ý 1

`ss` có trên cả Ubuntu và Rocky (gói iproute); `netstat` và `lsof` thì không chắc. Xem `ss -h` cho các cờ chọn TCP, chỉ
socket đang nghe, không phân giải tên và bỏ dòng tiêu đề.

### Gợi ý 2

Cột địa chỉ có thể là `127.0.0.1:28080`, `[::]:22`, `127.0.0.53%lo:53` hay `*:22`. Lấy phần sau dấu `:` **cuối cùng**
rồi so bằng phép so bằng, không dùng `grep ":$port"`.

### Gợi ý 3

Với user thường, `ss -p` chỉ in phần `users:(...)` cho socket của tiến trình user đó sở hữu. Đừng đoán tên từ cổng
("22 chắc là sshd"): báo cáo gửi khách chỉ ghi điều đo được.
