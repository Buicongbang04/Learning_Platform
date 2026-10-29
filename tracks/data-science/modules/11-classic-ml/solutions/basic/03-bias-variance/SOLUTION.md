# Lời giải: đo bias và variance bằng mô phỏng

## Cách làm

Ý tưởng là coi tập train là **biến ngẫu nhiên**. Với mỗi điểm test cố định, dự đoán của model là một phân
phối (qua các tập train khác nhau). Bias là độ lệch của trung bình phân phối đó so với f; variance là độ rộng
của nó. Đẳng thức `bias² + variance = mean((preds − f)²)` đúng chính xác (không xấp xỉ) khi variance tính với
ddof = 0, vì đó là phân rã trung bình bình phương quanh trung bình mẫu.

## Kết quả (f = sin 2πx, σ = 0.3, n_train = 60, 300 lần)

| k | bias² | variance | tổng (+ noise 0.09) |
| --- | --- | --- | --- |
| 1 | 0.000 | 0.094 | 0.185 |
| 7 | 0.001 | 0.018 | 0.109 |
| 30 | 0.069 | 0.015 | 0.174 |

(Mã trong mục 1 của README module.) k = 1 có variance lớn hơn cả noise: mỗi dự đoán là đúng một điểm train,
mang nguyên nhiễu của điểm đó. k = 30 lấy trung bình nửa tập train, làm phẳng hình sin: bias tăng. Điểm cân bằng
ở giữa.

## Từ mô phỏng sang thực tế

Ngoài đời không rút được 300 tập train. Thay bằng:

- Khoảng cách train/validation (variance) và mức sai số chung (bias).
- Learning curve: variance giảm khi thêm dữ liệu, bias thì không.
- Độ dao động của điểm CV giữa các fold: một dấu hiệu gián tiếp của variance.

Bagging (random forest) là cách giảm variance mà không tăng bias nhiều: chính là lấy trung bình dự đoán qua
nhiều tập train (bootstrap), đúng thứ ta làm trong mô phỏng.
