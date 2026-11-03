---
title: Cài quillo ở khách air-gapped từ "USB"
level: intermediate
services: []
files:
  - path: starter/pack_usb.sh
    note: 3 TODO, POSIX sh, chạy trên máy bạn
  - path: starter/install.sh
    note: 6 TODO, bash, chạy bằng sudo trên máy lawfirm-staging
  - path: tests/test_quillo_airgapped.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lawfirm-staging
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - uv run pytest tracks/fde/modules/03-airgapped-proxy/exercises/intermediate/02-quillo-airgapped -q -s
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Lần đầu mang sản phẩm thật vào một khách không có internet: chuẩn bị đủ mọi thứ ở văn phòng, chép qua kênh duy nhất
khách cho phép, kiểm toàn vẹn ở phía khách **trước** khi đụng vào bất cứ gì, rồi dựng `quillo` chạy từ registry nội bộ
của khách. Thiếu một thứ là mất một chuyến đi; cài bundle hỏng là mất lòng tin của IT khách.

## Đề bài

Công ty luật cho bạn cài `quillo` 1.0.0 lên máy staging `lawfirm-staging` (Ubuntu 22.04, có sudo, **không** ra internet,
không DNS). Quy định của họ: phần mềm vào vùng trong chỉ qua một ổ USB đã quét virus; mọi image chạy trong vùng trong
phải đến từ registry nội bộ `10.0.2.101:5000`. Sản phẩm, cách cài một node và các biến cấu hình: `tracks/fde/product/README.md`.

**`starter/pack_usb.sh <quillo-1.0.0.tar> <thư mục công cụ> <thư mục USB>`** chạy trên máy bạn và chuẩn bị nội dung
USB. Test chạy nó trong sandbox (`testkit.run_sandboxed`, chỉ ghi được trong thư mục tạm chứa thư mục USB, ≤120 s) với
bundle `tracks/fde/product/dist/quillo-1.0.0.tar` và thư mục công cụ `data/raw/fde-tools/`: mọi công cụ bạn cần mang theo
phải được tải sẵn vào đó **trước** (phần `0. Cài đặt` của README module có sẵn một binary đã ghim; cần thêm thì tự tải,
ghim phiên bản và sha256 như vậy). Ở thư mục gốc của USB phải có `quillo-1.0.0.tar` (giữ nguyên byte của bản phát
hành), `install.sh`, và `SHA256SUMS` theo định dạng của `sha256sum` (mỗi dòng `<64 ký tự hex>  <đường dẫn tương đối từ gốc
USB>`) có ít nhất dòng của `quillo-1.0.0.tar`.

**`starter/install.sh`** nằm trên USB. Test chép **cả thư mục USB** vào `/home/fde/usb/` của máy staging (đây là "cắm
USB": bản chép do cổng chuyển tệp của khách thực hiện), rồi chạy từ `/tmp`:

```bash
sudo bash /home/fde/usb/install.sh
```

Thứ tự test làm:

1. Đổi **một byte** ở giữa `quillo-1.0.0.tar` trên USB (chép hỏng), chạy `install.sh`.
2. Giữ byte hỏng đó (nằm trong một tệp của bundle), đồng thời viết lại dòng của `quillo-1.0.0.tar` trong `SHA256SUMS` cho
   khớp với tệp đã hỏng (ai đó sửa cả USB lẫn danh sách checksum), chạy `install.sh`.
3. Trả byte và `SHA256SUMS` về như cũ, chạy lại `install.sh`.

Test boot VM 5120 MB. Lần chạy có bundle hỏng và lần cài thật mỗi lần ≤240 s. Đo trên máy của repo: cả bài 94–146 s (tuỳ tải máy).
Tự boot máy để điều tra: `with fdekit.customer_site("lawfirm-staging", memory_mb=5120, forwards=(18080,)) as s:`.

## Tiêu chí đạt

`test_install_quillo_from_usb_on_lawfirm_staging`:

- `pack_usb.sh` thoát `0`; USB có `quillo-1.0.0.tar`, `install.sh` và `SHA256SUMS` (có dòng cho `quillo-1.0.0.tar`) ở gốc.
- Bundle hỏng một byte: `install.sh` thoát khác `0`, và **chưa** làm gì với Docker hay registry: registry nội bộ không có
  repository nào, `docker images -q` và `docker ps -aq` trong VM rỗng.
- Bundle có một tệp bị sửa nhưng `SHA256SUMS` đã bị viết lại cho khớp (bước 2): `install.sh` cũng thoát khác `0` với cùng
  điều kiện "chưa làm gì": registry rỗng, không image, không container.
- Bundle đúng: `install.sh` thoát `0`; trong 60 s, `GET /healthz` qua cổng 18080 của VM (forward ra host) trả 200 với
  `"version": "1.0.0"`.
- Project compose tên `quillo` có đủ các dịch vụ `db`, `llm`, `embed`, `api`, `worker` đang chạy; image của **mỗi** dịch
  vụ có tên bắt đầu bằng `10.0.2.101:5000/` và đúng `repo:tag` đó có trong registry nội bộ (hỏi từ host qua API `/v2/`).

## Gợi ý

### Gợi ý 1

Trước khi viết `pack_usb.sh`, làm một vòng khảo sát `lawfirm-staging` như ở module 01, nhưng nhắm vào câu hỏi: những lệnh
mà hướng dẫn "Cài từ bundle" của sản phẩm dùng, lệnh nào **có** trên máy này, bản nào? Thứ gì thiếu phải nằm trên USB.

### Gợi ý 2

Có hai lớp toàn vẹn: bản chép USB có giống bản bạn đã đóng gói không, và bundle có giống bản công ty phát hành không.
Lớp nào kiểm được mà không cần giải nén? Lớp nào cần công cụ có sẵn trên máy khách (đừng giả định Python của khách mới
như máy bạn)?

### Gợi ý 3

Compose của sản phẩm ghi tên image gốc. Bạn không cần sửa `compose.yaml` của bundle (sửa thì sha256 trong manifest không
còn khớp); compose cho phép chồng thêm tệp cấu hình thứ hai.
