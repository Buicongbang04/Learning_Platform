---
title: Thiết kế lineage và chiến lược versioning cho ba hệ thống dữ liệu
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Chọn và biện minh công cụ versioning dữ liệu (DVC, lakeFS, Delta Lake hoặc kết hợp) cho ba ràng buộc khác nhau, và chứng minh
mỗi thiết kế trả lời được câu hỏi "model này sinh từ dữ liệu nào".

## Đề bài

Viết `design.md` (dưới 3 trang) cho ba hệ thống:

- **A**: đội ML 4 người, 3 GB Parquet mỗi tháng từ NYC TLC, huấn luyện lại hằng tuần, cần tái lập mọi model trong 12 tháng.
- **B**: data lake 40 TB trên S3, năm job Spark của ba đội cùng ghi, hay ghi dở dang, cần commit nguyên tử, branch để thử đổi pipeline, rollback cả lake.
- **C**: bảng `trips` Delta/Parquet được ghi liên tục từ stream, cần truy vấn "bảng này lúc 03:00 hôm qua trông thế nào" cho điều tra sự cố.

Với mỗi hệ thống nêu: công cụ chọn và hai phương án bị loại cùng lý do, cách **một phiên bản dữ liệu được gắn với một commit code và một model** (tên trường, nơi lưu), chi phí vận hành
(ai trực, thành phần phải chạy), chính sách giữ dữ liệu (retention, garbage collection), và một kịch bản hỏng (vd. xoá nhầm object ở remote) cùng cách phát hiện.

Cuối bài trả lời: sáu tháng sau, người mới được hỏi "tái lập model đang chạy production và chỉ ra nó học từ dữ liệu nào". Liệt kê chính xác các lệnh hoặc truy vấn người đó chạy ở hệ thống A.

## Tiêu chí đạt

- Ba hệ thống đều có công cụ chọn kèm hai phương án loại và lý do gắn với ràng buộc, không phải sở thích.
- Mỗi hệ thống nêu cụ thể trường lineage (vd. tên tag, chỗ lưu hash) và vì sao nó đủ để tái lập.
- Có chính sách retention và một kịch bản hỏng kèm cách phát hiện.
- Phần "sáu tháng sau" là chuỗi lệnh chạy được, không phải mô tả chung.

## Gợi ý

### Gợi ý 1

Phân biệt hai câu hỏi: "dựng lại đúng dữ liệu của một lần huấn luyện" và "nhiều writer cùng ghi có nhất quán không". Mỗi công cụ trả lời tốt một trong hai.

### Gợi ý 2

Lineage chỉ đáng tin nếu nó được ghi tự động ở thời điểm chạy, không do con người nhớ điền.
