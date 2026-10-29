# Hướng làm: thiết kế thí nghiệm cho Olist

## Baseline trên Olist thật

| Con số | Giá trị |
| --- | --- |
| `bad_review_rate` | 12.8% |
| `late_rate` | 8.1% |
| `bad_review_rate_late` | 54.1% |
| `delivered_per_week` (trung vị cả giai đoạn) | 937 |

`delivered_per_week` trên toàn bộ dữ liệu bị kéo xuống bởi giai đoạn 2016 – đầu 2017 khi Olist còn
nhỏ. Trung vị từ 06/2017 tới 07/2018 là khoảng 1 259. Thiết kế tốt dùng traffic **gần đây và ổn
định** nhất, và nêu rõ đã chọn khoảng nào.

## Các quyết định thiết kế cần cân nhắc

**Tổng thể.** Chỉ đơn được model dự đoán có nguy cơ trễ (ví dụ ngưỡng xác suất cho top 10% đơn).
Tổng thể nhỏ (khoảng 100–150 đơn mỗi tuần) nhưng baseline review xấu cao (30–50% tuỳ độ chính xác
model) và tác động kỳ vọng lớn hơn nhiều so với áp lên mọi đơn.

**Đơn vị random.** Theo đơn là đơn giản nhất; theo khách nếu khách có thể có nhiều đơn đồng thời
(tránh một khách nhận tin cho đơn này mà không cho đơn kia). Random tại thời điểm model chấm điểm,
lưu cả điểm model để phân tích theo mức rủi ro.

**OEC và selection bias.** OEC là tỉ lệ review ≤ 2 sao, nhưng review là tự nguyện: nếu tin nhắn
làm khách bực ít đi, có thể họ **không viết review** thay vì viết review tốt. Guardrail bắt buộc:
tỉ lệ có review. Phương án mạnh hơn: OEC trên mọi đơn được random, với "không review" là một nhóm
riêng, hoặc dùng metric hành vi (khách quay lại mua trong 90 ngày).

**Power.** Ví dụ baseline 40%, muốn phát hiện giảm 5 điểm phần trăm: khoảng 1 470 đơn mỗi nhóm,
tức 20–30 tuần với 100–150 đơn nguy cơ mỗi tuần. Không khả thi: cân nhắc MDE lớn hơn, mở rộng
ngưỡng nguy cơ (tổng thể lớn hơn nhưng baseline thấp hơn, phải tính lại), CUPED với lịch sử review
của khách (module 04), hoặc kết hợp nhiều thị trường.

**Thời lượng.** Cộng thời gian giao hàng còn lại và thời gian khách viết review (phần lớn trong 1–2
tuần sau giao) trước khi đọc kết quả.

**Rủi ro.** Model thay đổi trong lúc chạy (đóng băng phiên bản model); nhắn tin cho đơn cuối cùng
giao đúng hẹn có thể gây lo lắng không cần thiết; voucher làm thay đổi hành vi mua (guardrail chi
phí); đội CSKH quá tải.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Baseline đúng và đúng tổng thể | 15 | Dùng baseline của tổng thể thí nghiệm, nêu rõ khoảng thời gian |
| Đơn vị random | 10 | Có lý do, nhận ra rủi ro nhiễm chéo |
| Metric | 20 | OEC định nghĩa chính xác; ≥ 2 guardrail có lý do; nhận ra selection bias của review |
| Power | 20 | Tính đúng, đánh giá khả thi, đề xuất thay đổi khi không khả thi |
| Kế hoạch phân tích | 15 | Kiểm định, SRM, multiple testing, segment định trước, quy tắc dừng |
| Quy tắc quyết định | 10 | Viết trước, có guardrail cứng |
| Rủi ro | 10 | Ít nhất 3 rủi ro thực tế kèm cách phòng |

Đạt từ 70 điểm trở lên là đủ đưa vào experiment review ở một công ty có văn hoá thí nghiệm.
