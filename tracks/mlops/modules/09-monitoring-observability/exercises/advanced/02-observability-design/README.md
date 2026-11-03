---
title: Thiết kế quan sát cho nền tảng ETA và giá cước
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung thiết kế, điền mọi TODO
  - path: tests/fixtures/DESIGN.bad.md
    note: Ví dụ thiết kế yếu, test dùng để kiểm bộ kiểm tra
  - path: tests/test_design.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/advanced/02-observability-design -q
---

## Mục tiêu

Thiết kế cách quan sát hai service ML: chọn metric và tính được cái giá của chúng bằng số series, chọn alert theo triệu chứng,
và quyết định log, trace giữ bao lâu, lấy mẫu thế nào.

## Đề bài

Công ty taxi chạy service ETA (khoảng 20 pod, 400 yêu cầu mỗi giây giờ cao điểm) và service giá cước (10 pod, 80 yêu cầu mỗi giây)
trên một cụm. Hiện chỉ có CPU và RAM của node. Hai sự cố gần đây khách báo trước đội: model sai version trả ETA 999 giây (HTTP vẫn 200),
và ETA đúng nhưng chậm gấp ba. Nhãn thật về muộn 30 tới 90 phút. Ràng buộc: một Prometheus 512 MB, **ngân sách 20 000 series**, một
người trực mỗi tuần, log chứa dữ liệu khách hàng.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 6.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và giả định | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Kiến trúc | Khối ` ```mermaid ` có ít nhất 6 cạnh (`-->`, `->>` hoặc `---`) |
| 3. Danh mục metric và ngân sách series | Bảng ít nhất 8 dòng đủ 4 cột (`Metric`, `Loại`, `Label`, `Series tối đa`); `Loại` là `counter`, `gauge`, `histogram` hoặc `info`; cột `Label` ghi dạng `tên(số giá trị)` cách nhau dấu phẩy, hoặc `-`; `Series tối đa` là số nguyên **không nhỏ hơn tích số giá trị của các label**; không dùng label `request_id`, `user_id`, `trip_id`, `session_id`, `rider_id`, `driver_id`, `ip`, `email`, `url`, `path`, `timestamp`; tổng cột `Series tối đa` không quá 20 000; có ít nhất một `histogram` và một `info` |
| 4. Alert và runbook | Bảng ít nhất 6 dòng đủ 5 cột (`Alert`, `Triệu chứng`, `Severity`, `for`, `Runbook`, không ô nào trống); `Severity` chỉ `critical` hoặc `warning`, ít nhất 1 critical và 2 warning; `for` dạng `5m` từ 1m; critical không được theo nguyên nhân (nhắc CPU, RAM, đĩa trong tên hay triệu chứng); có alert về metric của model (nhắc `prediction`, `fallback`, `phân phối` hoặc `dự đoán`) và một alert metric biến mất (nhắc `absent`, `mất metric` hoặc `biến mất`) |
| 5. Log và trace | Ít nhất 4 gạch đầu dòng, có nhắc `retention` và `sampling` |
| 6. Rủi ro và việc còn mở | Ít nhất 3 gạch đầu dòng |

Test còn đưa một thiết kế yếu (`tests/fixtures/DESIGN.bad.md`) vào cùng bộ kiểm tra và đòi nó bị bắt. Nội dung chấm bằng rubric
trong `solutions/advanced/02-observability-design/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/advanced/02-observability-design -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Mỗi alert và mỗi quyết định ở phần 3 truy được về một sự cố hoặc ràng buộc trong đề.
- Giải thích được vì sao `instance` phải có trong tích số series và vì sao log dự đoán có retention khác log truy cập.

## Gợi ý

### Gợi ý 1

Cho mỗi metric hỏi: câu hỏi nào của người trực nó trả lời? Metric không có câu hỏi thì bỏ. Rồi tính số series: tích số giá trị
của từng label nhân với số instance, histogram nhân thêm số bucket cộng ba.

### Gợi ý 2

Với "model sai version mà HTTP vẫn 200", hãy nghĩ tới tín hiệu nằm ở **nội dung** của dự đoán chứ không ở trạng thái HTTP. Với
nhãn về muộn, hỏi tín hiệu nào sớm hơn nhãn và đánh đổi của nó là gì.
