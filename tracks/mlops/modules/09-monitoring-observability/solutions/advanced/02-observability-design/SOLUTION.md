# Lời giải: thiết kế quan sát cho nền tảng ETA và giá cước

Bài Advanced không có đáp án duy nhất. `DESIGN.md` cạnh tệp này là một bản mẫu đã chạy qua test; chấm theo chất lượng lập luận.

## Các quyết định cốt lõi

- **Bắt đầu từ cách khách bị ảnh hưởng.** Hai sự cố trong đề (model sai version, chậm gấp ba) đều là triệu chứng; alert critical đo
  tỉ lệ lỗi và tốc độ đốt budget, không đo CPU. CPU và RAM vẫn có nhưng là metric để điều tra, không đánh thức ai.
- **Metric của model là một tầng riêng.** Phân phối dự đoán, tỉ lệ fallback và info metric phiên bản trả lời đúng câu
  "model sai version" mà RED không thấy: HTTP vẫn 200, độ trễ vẫn đẹp.
- **Ngân sách series tính bằng số.** Mỗi dòng ghi tích số giá trị label (kể cả `instance`) rồi nhân hệ số histogram; tổng phải dưới
  ngân sách. Người đọc thấy ngay cái giá của một label mới.
- **Log cho từng yêu cầu, metric cho tổng hợp, trace cho đường đi.** `request_id` chỉ có trong log và trace, không bao giờ trong metric.
- **Retention và sampling có lý do.** Log dự đoán giữ lâu vì nhãn về muộn; trace lấy mẫu theo đuôi để giữ đúng phần lỗi và chậm.
- **Runbook cho mọi alert.** Alert không runbook là alert chuyển việc suy nghĩ sang người trực lúc 3 giờ sáng.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Alert theo triệu chứng, đủ cả metric của model | 25 | Critical theo người dùng; có alert phân phối dự đoán hoặc fallback; có alert cho metric biến mất; `for` hợp lý |
| Cardinality và ngân sách series | 20 | Tính tích số đúng, có `instance`, histogram nhân bucket, tổng dưới ngân sách, không label theo yêu cầu |
| Kiến trúc và luồng dữ liệu | 15 | Sơ đồ có đủ metric, log, trace, alert, dashboard và ai nhận gì |
| Log và trace | 15 | Có cấu trúc, allow-list feature, retention theo mục đích, sampling có lý do, `request_id` nối ba tín hiệu |
| Vận hành người trực | 15 | Routing critical/warning, runbook, giảm nhiễu, ai sở hữu alert |
| Rủi ro, giới hạn | 10 | Nêu nhãn về muộn, mùa vụ, điểm hỏng đơn, cardinality ngầm |

Dưới 70: thường vì alert theo nguyên nhân (CPU, RAM), bảng metric không tính được số series, hoặc không nghĩ tới metric của model.
