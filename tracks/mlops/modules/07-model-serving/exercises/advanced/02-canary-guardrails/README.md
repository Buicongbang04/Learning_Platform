---
title: Kế hoạch canary với guardrail và tiêu chí rollback tự động
level: advanced
services: []
files:
  - path: starter/RUNBOOK.md
    note: Kế hoạch tung model mới của bạn
run: []
---

## Mục tiêu

Biến "canary 5% rồi xem" thành một kế hoạch có số: từng bước, chỉ số chặn, cỡ mẫu đủ để quyết định và điều kiện rollback không cần ai thức dậy.

## Đề bài

Service ETA taxi nhận khoảng 200 request/giây ở giờ cao điểm và 20 request/giây về đêm. Model mới (version 8) cải thiện MAE offline 4%. Dịch vụ có SLO: p95 dưới 150 ms, tỉ lệ lỗi dưới 1% (hiện 0.4%), MAE theo nhãn về sau (nhãn đến sau 30 phút). Định tuyến canary bằng hash `request_id` như bài `basic/02`, rollback bằng alias + reload như bài `intermediate/01`. Viết `starter/RUNBOOK.md` gồm:

1. **Các bước**: tỉ lệ canary từng bước (vd. 1%, 5%, 25%, 100%), thời gian dừng ở mỗi bước và lý do chọn thời gian đó.
2. **Guardrail**: ít nhất năm chỉ số có ngưỡng chặn (vận hành: lỗi, p95; mô hình: phân phối dự đoán, MAE theo nhãn trễ; nghiệp vụ nếu có), kèm cách so (canary với stable trong cùng cửa sổ, không so với hôm qua).
3. **Cỡ mẫu**: ở bước 1% giờ cao điểm có bao nhiêu request canary mỗi phút; bao lâu mới phát hiện được tỉ lệ lỗi tăng từ 0.4% lên 1.0%; bước nào không thể đủ mẫu về đêm và làm gì.
4. **Quy tắc rollback tự động**: điều kiện chính xác, ai hoặc cái gì thực hiện, và điều nó *không* làm (ví dụ không tự promote).
5. **Rủi ro còn lại**: điều canary không bắt được (nhãn trễ, mùa vụ, slice hiếm) và cách bù (shadow trước, slice riêng, thời gian dừng dài hơn).

## Tiêu chí đạt

- Có phép tính cỡ mẫu cụ thể (số request, thời gian), không chỉ "đủ lâu".
- Quy tắc rollback đo được và một người lạ áp dụng được.
- Tự chấm theo rubric trong `SOLUTION.md` sau khi làm xong.

## Gợi ý

### Gợi ý 1

Phát hiện 0.4% lên 1.0% với 95% tin cậy cần cỡ mẫu theo công thức hai tỉ lệ; ước lượng thô: vài trăm tới một nghìn request canary mỗi bên là mức bắt đầu có ý nghĩa.

### Gợi ý 2

Hỏi: trong 30 phút nhãn chưa về, chỉ số nào bảo vệ người dùng? Đó là guardrail vận hành và phân phối dự đoán; MAE theo nhãn chỉ chặn bước cuối.
