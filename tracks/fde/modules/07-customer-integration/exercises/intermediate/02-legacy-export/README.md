---
title: "Nạp export CSV của hệ thống cũ thành tài liệu cho quillo"
level: intermediate
services: []
files:
  - path: starter/legacy_export.py
    note: Bản đồng nghiệp viết thử; bạn viết lại
  - path: samples/HOPDONG.CSV
    note: Export thật của hệ thống quản lý hợp đồng (không sửa)
  - path: samples/DOITAC.CSV
    note: Export thật của hệ thống văn phòng đối tác (không sửa)
  - path: samples/expected
    note: Tài liệu cần có cho hai tệp mẫu, IT khách đối chiếu với màn hình hệ thống cũ (không sửa)
  - path: tests/test_legacy_export.py
    note: Không sửa
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit derive 07-customer-integration-quillo
  - uv run pytest tracks/fde/modules/07-customer-integration/exercises/intermediate/02-legacy-export -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Hai hệ thống cũ của công ty luật không có API, không cho đọc database; thứ duy nhất IT xuất được là CSV, chạy theo lịch
trên một máy Windows và thả vào thư mục chia sẻ. Một là phần mềm quản lý hợp đồng của chính công ty (viết từ những năm
2000), một là phần mềm của văn phòng đối tác ở Pháp mà công ty luật dùng chung. Khách muốn hỏi quillo về những hợp đồng
này. Bạn viết bộ chuyển đổi biến mỗi dòng export thành một tài liệu văn bản cho inbox của quillo, đúng **từng ký tự** như
trên màn hình hệ thống gốc, chạy lại được mỗi đêm.

## Đề bài

Viết lại `starter/legacy_export.py` (Python 3.12, thư viện chuẩn). Cách chạy:

```sh
python legacy_export.py --in <thư mục có HOPDONG.CSV và DOITAC.CSV> --out <thư mục đích>
```

Thư mục đích sau khi chạy chứa **đúng** một tệp cho mỗi dòng dữ liệu của hai export (không thêm tệp nào khác), ghi bằng
UTF-8, xuống dòng `\n`:

| Nguồn | Tệp | Nội dung (mỗi dòng kết thúc bằng `\n`) |
| --- | --- | --- |
| `HOPDONG.CSV` | `hop-dong/<Số HĐ>.txt` | `Nguồn: hệ thống hợp đồng` / `Số hợp đồng: …` / `Khách hàng: …` / `Loại hợp đồng: …` / `Ngày ký: YYYY-MM-DD` / `Giá trị: <số nguyên, không dấu phân cách> VND` / `Ghi chú:` / *ghi chú* |
| `DOITAC.CSV` | `doi-tac/<Réf>.txt` | `Nguồn: văn phòng đối tác` / `Mã hồ sơ: …` / `Khách hàng: …` / `Ngày mở: YYYY-MM-DD` / `Phí: <số, hai chữ số thập phân, dấu chấm> EUR` / `Ghi chú:` / *ghi chú* |

- *Ghi chú* giữ nguyên văn bản của ô, kể cả xuống dòng trong ô (thành `\n`), theo sau là `\n`; ô rỗng thì tệp kết thúc
  ngay sau dòng `Ghi chú:`.
- Văn bản (tên khách hàng, loại hợp đồng, ghi chú) phải **trùng từng code point** với văn bản IT khách đã đối chiếu từ
  màn hình hệ thống gốc: xem `samples/expected/` cho hai tệp mẫu.
- Dòng không có `Số HĐ`/`Réf` (vd. dòng tổng cuối export) không phải bản ghi.
- Chạy lại với cùng export cho đúng cùng kết quả.

Test (cả bài ~20 s trên máy của repo):

1. Chạy bộ chuyển đổi của bạn (trên host, sandbox `testkit.run_sandboxed`) với `samples/` và so với `samples/expected/`.
2. Sinh **hai bộ export mới** cùng định dạng, cùng hai hệ thống (bản ghi, ngày, số tiền, ghi chú ngẫu nhiên mỗi lần chạy
   test), chạy bộ chuyển đổi hai lần mỗi bộ, so kết quả với bản ghi gốc.
3. Boot `lab-open` có quillo 1.0.0 (snapshot dẫn xuất `07-customer-integration-quillo`), đặt các tệp bạn sinh ra vào
   inbox của quillo (giữ thư mục), chờ worker nạp.

## Tiêu chí đạt

- `test_samples`: thoát `0`; tập tệp và nội dung từng byte trùng `samples/expected/`.
- `test_fresh_exports_and_rerun`: với cả hai bộ export mới, cả lần chạy đầu và lần chạy lại: thoát `0`, đúng tập tệp,
  đúng nội dung từng byte.
- `test_quillo_ingests_documents`: không tệp nào vào `inbox/failed/`; trong 120 s, `GET /api/documents` (token quản
  trị) liệt kê đúng các tài liệu `hop-dong/…`, `doi-tac/…` với `doc_id` khớp nội dung cần có (quillo đặt `doc_id` theo
  sha256 nội dung tệp).

## Gợi ý

### Gợi ý 1

Một tệp văn bản không tự nói nó được mã hoá thế nào. Hệ thống viết cho Windows ở đâu, vào năm nào, thường lưu bằng bảng
mã nào? Thử giả thuyết trên những ký tự "khó" nhất của tệp mẫu, không phải trên chữ cái ASCII.

### Gợi ý 2

Hai chuỗi trông giống hệt nhau trên màn hình vẫn có thể khác nhau khi so bằng `==`. Khi so với `samples/expected/`
mà khác, in `repr()` hoặc từng code point của đoạn khác.

### Gợi ý 3

Đừng tách dòng bằng tay: ô có dấu phân cách, dấu ngoặc kép và xuống dòng bên trong là chuyện thường của CSV. Ngày tháng
thì tìm trong tệp mẫu một bản ghi không thể đọc theo hai cách.
