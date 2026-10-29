# Thiết kế thí nghiệm: nhắn tin chủ động cho đơn có nguy cơ giao trễ

Tài liệu pre-registration, viết **trước** khi chạy thí nghiệm. Người đọc: PM, đội vận hành, đội
CSKH, DS khác review thiết kế. Xoá mọi dòng TODO khi viết xong. Mọi con số lấy từ `baseline()` trên
Olist thật.

## 1. Bối cảnh và giả thuyết

TODO: vấn đề kinh doanh (dùng số thật: review xấu ở đơn trễ và đơn đúng hẹn), can thiệp đề xuất,
giả thuyết và cơ chế vì sao tin nó hiệu quả.

## 2. Tổng thể và đơn vị random

TODO: ai đủ điều kiện vào thí nghiệm (đơn được dự đoán có nguy cơ trễ? mọi đơn?), random ở thời
điểm nào, theo đơn hay theo khách, vì sao. Rủi ro nhiễm chéo.

## 3. Metric

TODO: OEC (định nghĩa chính xác, cửa sổ thời gian), guardrail (ít nhất 2, kèm lý do), metric chẩn
đoán. Bàn về việc tin nhắn có thể làm thay đổi *ai* để lại review (selection bias trên chính OEC).

## 4. Power, cỡ mẫu, thời lượng

TODO: baseline của đúng tổng thể thí nghiệm, MDE (lý do kinh doanh), α, power, cỡ mẫu mỗi nhóm,
thời lượng (gồm thời gian chờ review). Nếu không khả thi thì đề xuất thay đổi gì.

## 5. Kế hoạch phân tích

TODO: kiểm định cho OEC và guardrail, kiểm tra SRM, xử lý multiple testing, segment sẽ xem (định
trước), có dừng sớm không và theo quy tắc nào.

## 6. Quy tắc ra quyết định

TODO: kết quả thế nào thì ship, không ship, chạy tiếp. Guardrail nào là "cứng".

## 7. Rủi ro và giới hạn

TODO: những gì có thể làm hỏng thí nghiệm và cách phòng.
