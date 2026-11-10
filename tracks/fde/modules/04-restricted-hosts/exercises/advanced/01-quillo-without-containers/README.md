---
title: Thiết kế cài quillo không container
level: advanced
services: []
files:
  - path: starter/install-plan.md
    note: Khung kế hoạch cài 7 phần
run: []
---

## Mục tiêu

Có khách nói thẳng: "máy chủ này không chạy container, không có ngoại lệ". Sản phẩm của bạn chỉ phát hành dạng compose.
Trước khi nói "không làm được", FDE phải biết chính xác cần gì để chạy **cùng mã đó** không có container, cái giá vận hành
là gì, và viết thành một kế hoạch mà product, IT khách và người trực sau bạn đều đọc được.

## Đề bài

Ngân hàng (máy giống hồ sơ `bank`: Rocky Linux 8.10, SELinux enforcing, không sudo cho tài khoản dịch vụ `svc-quillo`,
không mạng, 4 vCPU, 16 GB RAM, `/tmp` noexec theo baseline CIS, `nofile` 4096) muốn chạy thử `quillo` 1.1.0 cho phòng
pháp chế. Chính sách: không container runtime nào trên máy chủ sản xuất; Postgres 16 do đội DBA cấp (một database
`quillo`, user `quillo`, extension `vector` 0.8 đã cài, kết nối qua TLS bằng CA nội bộ của ngân hàng, máy
`db01.bank.internal:5432`). Người dùng truy cập qua reverse proxy của ngân hàng (TLS), proxy gọi tới máy quillo ở cổng do
bạn chọn. IT cấp linger cho `svc-quillo` nếu bạn xin.

Đọc `tracks/fde/product/README.md`, `compose.yaml`, `Dockerfile` của sản phẩm để biết mỗi dịch vụ chạy gì, bằng lệnh nào,
với biến nào. Viết `starter/install-plan.md` gửi product và IT ngân hàng. Bài không có test; tự chấm theo rubric, đạt
đủ 8 mục, rồi so với bài mẫu trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| R1 | Bảng ánh xạ **mọi** dịch vụ của compose (`db`, `llm`, `embed`, `api`, `worker`) sang cách chạy không container: chương trình, phiên bản, lệnh/đối số tương đương, user, thư mục, cổng (chỉ `127.0.0.1` trừ cổng reverse proxy gọi tới) |
| R2 | Bundle: từng thành phần (Python runtime, wheelhouse của `quillo-api` theo `requirements.lock`, binary llama.cpp, model GGUF, migration, unit systemd), nguồn, cách ghim (phiên bản + sha256), điều kiện tương thích với máy đích (glibc, CPU flags như AVX2, Python) và cách kiểm trước khi cài |
| R3 | Bố cục cài trong `$HOME` của `svc-quillo` (bản phát hành, `current`, cấu hình, dữ liệu, log), unit `systemd --user` cho từng tiến trình với thứ tự phụ thuộc, `Restart=`, giới hạn tài nguyên trong khả năng của user, và cách đưa secret vào (tệp quyền `0600`, không nằm trên dòng lệnh) |
| R4 | Mọi điểm "máy bị khoá" được xử lý cụ thể: linger, `/tmp` noexec (chỗ nào trong stack dùng thư mục tạm), `nofile`, SELinux (domain của unit user, có cần nhãn hay boolean nào không và vì sao), cổng ≥ 1024 |
| R5 | Kết nối Postgres của DBA: URL kết nối không lộ mật khẩu ra `ps`/log, TLS kiểm chứng chỉ bằng CA nội bộ (`sslmode=verify-full`), quyền tối thiểu xin DBA (migration cần gì), và ai làm backup |
| R6 | Nâng cấp và rollback: 1.1.0 → bản sau với migration; thứ tự dừng/khởi động, điểm không quay lại, cách quay về |
| R7 | So sánh với đường compose: mất gì (cô lập, `read_only`, `no-new-privileges`, image đã quét), được gì, ai chịu chi phí bảo trì thêm (vá Python runtime, llama.cpp), và đề xuất chính thức cho product (hỗ trợ hay không, điều kiện) |
| R8 | Danh sách việc xin IT/DBA (mỗi việc một lệnh hoặc một quyền cụ thể, lý do, cách kiểm) và ít nhất 4 câu hỏi còn mở |

## Tiêu chí đạt

- `install-plan.md` đạt đủ R1–R8 khi tự chấm từng mục.
- Mọi lệnh, biến, đường dẫn trong kế hoạch lấy từ sản phẩm thật (`compose.yaml`, `Dockerfile`, README của sản phẩm) hoặc
  từ tài liệu chính thức của công cụ, không đoán.

## Gợi ý

### Gợi ý 1

Đọc `compose.yaml` như một bản đặc tả: với mỗi dòng (`user:`, `read_only:`, `tmpfs:`, `security_opt:`, `healthcheck:`,
`depends_on:`, `command:`), viết ra thứ tương đương trong unit systemd, hoặc ghi rằng không có tương đương.

### Gợi ý 2

Image `quillo-api` dựng từ `requirements.lock` có hash. Một wheelhouse phải khớp đúng lockfile đó trên Python và glibc
của **máy đích**, không phải máy bạn.

### Gợi ý 3

Binary llama.cpp dựng sẵn từ trang phát hành được biên dịch cho một tập lệnh CPU và một glibc cụ thể. Hỏi máy khách CPU gì
trước khi chọn bản.
