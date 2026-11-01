---
title: Sự cố - worker order-sync mất 10 giây mới dừng và xử lý trùng đơn
level: intermediate
services: []
files:
  - path: starter/Dockerfile
    note: Dockerfile đang chạy trên production
  - path: starter/entrypoint.sh
    note: Script khởi động đang chạy trên production
  - path: starter/worker.py
    note: Code worker của team ứng dụng
  - path: tests/test_shutdown.py
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/06-containers/exercises/intermediate/01-incident-slow-shutdown -q
---

## Mục tiêu

Chẩn đoán một sự cố vòng đời container từ triệu chứng (thời gian dừng, mã thoát, log) thay vì đoán, sửa tối thiểu ở đúng tầng,
và chứng minh bằng hành vi rằng container đã dừng sạch.

## Đề bài

`order-sync` là worker của Olist Shop đồng bộ đơn hàng từ hàng đợi theo region. Team ứng dụng khẳng định worker xử lý SIGTERM
đúng: nhận tín hiệu thì hoàn tất batch đang dở, ack, in log rồi thoát 0, và họ đã kiểm bằng `python worker.py` rồi Ctrl-C trên máy
dev. Image được build từ `starter/`.

Triệu chứng ghi nhận trên production:

- Mỗi lần rolling deploy, mỗi container cũ mất **đúng khoảng 10 giây** mới dừng; deploy 12 bản kéo dài 2 phút thay vì 20 giây.
- `docker ps -a` cho container cũ trạng thái `Exited (137)`.
- Log của container cũ dừng ở dòng `order-sync sẵn sàng`; không bao giờ có dòng `nhận tín hiệu` hay `dừng sạch`.
- Sau mỗi deploy, bộ phận tài chính thấy một số đơn bị đồng bộ hai lần (batch đang dở không được ack trước khi container chết).
- Chạy trên máy dev bằng Ctrl-C thì worker dừng sạch ngay.

Tìm nguyên nhân và sửa trong `starter/`. Giữ nguyên hành vi hiện có: queue suy ra từ biến `REGION` (`olist-orders-<REGION>`,
mặc định `sa-east-1`) như script khởi động đang làm. Không đổi logic xử lý của worker.

**Cách test chấm.** Test build `starter/` bằng `DockerLab.build`, chạy container với `REGION=us-east-1`, chờ log
`order-sync sẵn sàng`, rồi `docker stop -t 10` (qua `DockerLab.stop`) và đo thời gian.

## Tiêu chí đạt

- `docker stop` xong trong dưới 5 giây (grace period là 10 giây).
- Container thoát mã 0 (`State.ExitCode`).
- Log có hai dòng JSON do chính worker in: `nhận tín hiệu, hoàn tất batch đang dở` với `"signal": "SIGTERM"`, rồi
  `đã ack batch cuối, dừng sạch` có trường `batches`. Dòng chữ do script in ra không tính.
- Log có queue `olist-orders-us-east-1`: script khởi động vẫn chạy và vẫn đọc `REGION`.
- Một test build bản production lúc sự cố (`tests/fixtures/incident/`) và đòi nó tái hiện đúng triệu chứng: dừng mất ít nhất 8
  giây, mã 137, worker không log tín hiệu nào. Một test khác build một bản "sửa" giả (`tests/fixtures/trap-only/`: dừng nhanh, mã 0,
  in chữ `dừng sạch`, nhưng worker không nhận SIGTERM) và đòi phép kiểm trên bắt được nó.
- Giải thích được vì sao Ctrl-C trên máy dev không tái hiện được lỗi.

## Gợi ý

### Gợi ý 1

Mã 137 là 128 + 9. Đếm xem ai gửi tín hiệu nào cho tiến trình nào: `docker stop` gửi STOPSIGNAL của image tới đúng **một**
tiến trình trong container. Log `order-sync sẵn sàng` in ra `pid` của worker; so nó với PID mà `docker stop` nhắm tới.

### Gợi ý 2

Dựng lại môi trường sự cố rồi xem cây tiến trình từ máy host: `docker top <container>` hoặc
`docker exec <container> cat /proc/1/cmdline | tr '\0' ' '`. Mục 4 của lý thuyết giải thích vì sao tiến trình nào giữ PID 1
lại quan trọng.
