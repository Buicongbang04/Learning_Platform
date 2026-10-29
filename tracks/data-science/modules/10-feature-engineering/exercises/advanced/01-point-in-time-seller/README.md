---
title: Feature lịch sử seller point-in-time
level: advanced
services: []
files:
  - path: starter/seller_history.ipynb
    note: Hàm seller_history + cell explore so sánh
  - path: starter/REPORT.md
    note: Báo cáo cho DS sẽ đưa feature vào production
  - path: tests/test_seller_history.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/10-feature-engineering/exercises/advanced/01-point-in-time-seller/starter/seller_history.ipynb
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/advanced/01-point-in-time-seller -q
---

## Mục tiêu

Tính một feature tổng hợp theo thời gian (aggregate feature) đúng cách: tại mỗi thời điểm dự đoán,
chỉ dùng thông tin đã có trước đó. Đây là kỹ năng phân biệt DS làm được model chạy thật với DS chỉ
làm được model đẹp trên notebook, và là nền cho feature store ở module MLOps.

## Đề bài

1. Cài `seller_history(df, prior, smoothing=20)` trong notebook, theo docstring: với mỗi đơn, đếm
   các đơn **khác** của cùng seller có nhãn được biết (`label_time`) **trước** thời điểm dự đoán
   (`prediction_time`), và tỉ lệ review xấu của chúng làm trơn về `prior`. Phải chạy nhanh: 100
   nghìn dòng dưới 5 giây.
2. Chạy các cell `explore`: gắn feature vào bảng Olist (dự đoán lúc giao, nhãn biết lúc khách trả lời
   review), rồi so bốn cách đưa thông tin seller vào cùng một model logistic.
3. Viết `REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- Đúng trên bộ dữ liệu nhỏ có đủ bẫy: so sánh chặt, nhãn của chính đơn đến trước lúc giao, seller khác
  không lẫn vào, dòng không theo thứ tự, index không phải 0..n−1.
- Khớp cách tính brute force trên 300 dòng ngẫu nhiên; 100 nghìn dòng (có một seller chiếm 10%) dưới
  5 giây.
- Trên Olist thật: seller lớn nhất có 1 792 review quá khứ ở đơn cuối; 2.0% đơn validation thuộc seller
  chưa có lịch sử.
- `REPORT.md` không còn TODO, ít nhất 300 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Brute force (với mỗi dòng, lọc mọi dòng cùng seller) đúng nhưng là O(n²) trong mỗi seller. Hướng
nhanh: coi mỗi nhãn là một "event" (seller, label_time, bad), sắp theo thời gian và cộng dồn theo
seller; với mỗi đơn, tìm event cuối cùng của seller đó có `label_time < prediction_time`.
`pd.merge_asof(..., by="seller_id", allow_exact_matches=False)` làm đúng việc này.

### Gợi ý 2

`merge_asof` cần cả hai bảng sắp theo cột thời gian, và sẽ đếm cả nhãn của chính đơn nếu nhãn đó đến
trước lúc giao (khoảng 5% đơn Olist). Trừ nó ra sau khi join. Giữ một cột vị trí để trả kết quả về
đúng thứ tự dòng ban đầu.
