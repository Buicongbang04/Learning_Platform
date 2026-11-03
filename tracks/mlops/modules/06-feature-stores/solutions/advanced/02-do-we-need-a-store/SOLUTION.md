# Lời giải: cần feature store không

`decisions.yaml` cạnh tệp này là một bản mẫu đã qua test.

| Ca | Quyết định | Lập luận chính |
| --- | --- | --- |
| S1 | `none` | Theo lô, không online; bảng trong kho là đủ |
| S2 | `none` | Feature đến từ thân yêu cầu, thư viện chung cho cả train và serve đã loại skew; không có gì để tra |
| S3 | `feast` | Nhiều model dùng chung feature, cần online và point-in-time; đội 2 người tự host vừa sức với dữ liệu theo giờ |
| S4 | `managed` | Streaming vài giây, SLA, kiểm toán, đội nhỏ có ngân sách: mua vận hành |
| S5 | `none` | Skew do tính lại ở hai nơi: một hàm dùng chung và test parity là cách rẻ nhất; feature store là quá cỡ cho một model |
| S6 | `none` | Feature tổng hợp theo tháng cho model theo lô: bảng và dbt đã chia sẻ được |

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Quyết định đúng ở 6 ca | 30 | Cả 6 ca khớp; ca sai trừ 5 điểm |
| Lập luận dựa trên ràng buộc | 30 | Mỗi lý do nêu ràng buộc cụ thể của ca (độ trễ, số model, đội, độ tươi), không chung chung |
| Phân biệt triệu chứng và nguyên nhân (S5) | 20 | Chỉ ra nguyên nhân gốc, cách sửa rẻ nhất và phép kiểm parity |
| Biết chi phí của feature store | 10 | Nhắc điểm sự cố mới (online store), vận hành, độ phức tạp |
| Điều kiện đổi quyết định | 10 | Nêu ngưỡng làm S1, S5, S6 chuyển thành `feast` |

Lỗi hay gặp: coi feature store là đích đến thay vì công cụ giải một vấn đề cụ thể; chọn `managed` chỉ vì ngân sách có sẵn
mà không có ràng buộc streaming hoặc SLA.
