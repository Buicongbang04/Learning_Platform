# Lời giải: holdout và feedback loop

## Cách làm

- `naive_effect` so đơn được nhắn với mọi đơn khác. Trên dữ liệu giả lập, đơn được cảnh báo có rủi ro
  nền cao gấp vài lần đơn thường, nên dù tin nhắn giảm thật 10 điểm %, chênh lệch ngây thơ vẫn **dương**:
  dashboard sẽ kết luận "nhắn tin làm review xấu hơn". Đây là confounding (module 06) do chính model tạo
  ra.
- `holdout_effect` chỉ so **trong** nhóm flagged: treated và holdout cùng phân phối rủi ro nhờ random,
  nên chênh lệch là tác động nhân quả. SE không pooled vì không giả định hai tỉ lệ bằng nhau.
- `realized_value`: giá trị là hàm **giảm** của diff, nên cận dưới của giá trị đến từ cận trên của diff.
- `retraining_rows` là inverse propensity weighting đơn giản: trong nhóm flagged, xác suất một đơn
  không bị can thiệp là `holdout_share`, nên mỗi đơn holdout đại diện cho `1 / holdout_share` đơn.

## Chọn tỉ lệ holdout

Holdout là chi phí: đơn trong holdout không được giúp. Holdout lớn thì đo nhanh, holdout nhỏ thì đo
chậm. Với hệ thống Olist ở lý thuyết (khoảng 70 cảnh báo mỗi tuần, review xấu nền 26.8% ở nhóm cảnh
báo, tác động kỳ vọng 5.9 điểm %), holdout 20% cần khoảng 39 tuần, chia 50/50 lúc đầu cần khoảng 24
tuần. Cách làm phổ biến: 50/50 giai đoạn đầu để đo tác động, sau đó giữ holdout nhỏ (5–10%) lâu dài để
theo dõi tác động có phai đi không và để có dữ liệu retrain sạch.

## Bẫy thường gặp

- So "trước khi ra mắt" với "sau khi ra mắt": mùa vụ và khủng hoảng vận chuyển lẫn vào.
- Chọn holdout theo tiêu chí không ngẫu nhiên ("đơn CSKH không kịp xử lý"): không còn so sánh được.
- Retrain trên toàn bộ log, kể cả đơn đã được can thiệp: model tự phá chính nó qua mỗi vòng.
- Quên log `holdout` cùng với phiên bản model và điểm: không tái dựng được phân tích sau này.
