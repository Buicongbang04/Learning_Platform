# Design doc: hệ thống cảnh báo đơn có nguy cơ giao trễ cho Olist

Người đọc: DS và kỹ sư review thiết kế, PM, trưởng nhóm CSKH. Xoá mọi dòng TODO khi viết xong. Mọi con
số lấy từ code bạn đã chạy trên Olist thật (bài Basic 01–03, Intermediate 01–03 và `policy.py`).

## 1. Bối cảnh và mục tiêu

TODO: vấn đề kinh doanh bằng số thật (tỉ lệ trễ, review xấu ở đơn trễ và đúng hẹn), mục tiêu đo được,
và **phi mục tiêu** (non-goals): hệ thống này cố ý không làm gì.

## 2. Đóng khung bài toán

TODO: quyết định, người hành động, hành động, thời điểm dự đoán và vì sao chọn thời điểm đó (so với
lúc đặt hàng, và so với model review xấu "lúc đơn vừa giao" của module 10/11). Baseline không ML.

## 3. Metric

TODO: cây metric (business, online, offline, guardrail). Giá trị tiền của TP/FP, break-even precision,
và các giả định (C, V, Δ) cần business xác nhận.

## 4. Dữ liệu, nhãn và feature

TODO: định nghĩa nhãn, độ trễ của nhãn, bảng feature theo thời điểm có mặt, rủi ro leak và
training-serving skew.

## 5. Model

TODO: thang baseline → model, metric offline trên test theo thời gian, calibration, vì sao chọn.

## 6. Chính sách cảnh báo và năng lực vận hành

TODO: ngưỡng, trần mỗi tuần (dùng `weekly_late_volume` và `choose_policy`), điều gì xảy ra ở tuần
khủng hoảng, ai được báo khi số cảnh báo chạm trần.

## 7. Serving và fallback

TODO: batch hay online, tần suất, kiến trúc (có thể vẽ mermaid), log quyết định, fallback khi model hoặc
pipeline lỗi.

## 8. Monitoring và retrain

TODO: theo dõi gì khi nhãn về chậm, cảnh báo nào gọi người, chính sách retrain tránh feedback loop.

## 9. Thí nghiệm

TODO: holdout, cỡ mẫu và thời lượng (module 03), quy tắc ra quyết định.

## 10. Fairness và rủi ro

TODO: metric theo vùng, định nghĩa fairness chọn và vì sao, rủi ro khác (riêng tư, lạm dụng, seller).

## 11. Phương án đã loại

TODO: ít nhất hai phương án và vì sao loại.

## 12. Câu hỏi mở

TODO: những gì chưa biết và cách sẽ biết.
