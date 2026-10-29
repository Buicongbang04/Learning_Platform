# Lời giải: imbalanced data và calibration trên Telco churn

Notebook lời giải: `calibration.ipynb` (chạy được toàn bộ khi đã tải `telco-churn`).

## Prior correction

Model học trên tỉ lệ dương hiệu dụng $$\pi_s$$ (0.5 với `class_weight="balanced"`), dữ liệu thật có $$\pi$$.
Theo Bayes, likelihood ratio $$P(x \mid 1) / P(x \mid 0)$$ không đổi, chỉ prior đổi, nên odds dự đoán bị nhân
với một hằng số:

$$
\text{odds}_{\text{đúng}} = \text{odds}_{\text{model}} \cdot \frac{\pi / (1 - \pi)}{\pi_s / (1 - \pi_s)}
$$

Hệ quả: ngưỡng 0.5 trên model balanced (odds = 1) ứng với xác suất thật đúng bằng $$\pi$$. "class_weight cải
thiện recall" thường chỉ là đã hạ ngưỡng từ 0.5 xuống tỉ lệ dương.

## Kết quả (test 1 409 khách, churn thật 26.5%)

| Model | ROC-AUC | Brier | ECE | Xác suất trung bình |
| --- | --- | --- | --- | --- |
| logistic | 0.833 | 0.141 | 0.019 | 0.270 |
| logistic balanced | 0.832 | 0.173 | 0.154 | 0.419 |
| forest | 0.832 | 0.140 | 0.017 | 0.269 |
| forest balanced | 0.831 | 0.167 | 0.143 | 0.409 |

Sửa model balanced:

| | Thô | Sigmoid | Isotonic | Prior correction |
| --- | --- | --- | --- | --- |
| logistic balanced: Brier / ECE | 0.173 / 0.154 | 0.142 / 0.030 | 0.145 / 0.044 | 0.142 / 0.022 |
| forest balanced: Brier / ECE | 0.167 / 0.143 | 0.142 / 0.025 | 0.142 / 0.030 | 0.141 / 0.015 |

Forest không balanced, recalibrate: Brier 0.140 → 0.141 (sigmoid), 0.142 (isotonic); ECE 0.017 → 0.023, 0.032.

## Trả lời câu hỏi

1. Cả ba cách sửa là hàm đơn điệu của score, nên thứ hạng (ROC-AUC) giữ nguyên. Isotonic là hàm bậc thang: nhiều
   score khác nhau bị gộp vào cùng một giá trị, tạo tie, nên ROC-AUC có thể giảm chút ít (0.831 → 0.830).
2. Với `train_rate = 0.5`, p = 0.5 có odds 1; sau prior correction thành odds $$\pi/(1-\pi)$$, tức xác suất
   $$\pi \approx 0.265$$. Ngưỡng 0.5 trên model balanced tương đương ngưỡng khoảng 0.265 trên model calibrated.
3. Sigmoid khi tập calibration nhỏ (vài trăm ca) hoặc lệch có dạng "co giãn" đơn giản; isotonic khi có vài nghìn
   ca trở lên và lệch phức tạp. Với 1 409 khách, isotonic không hơn sigmoid và còn làm tệ đi model vốn đã
   calibrated.
4. Logistic hoặc forest **không** balanced (ECE khoảng 0.02, xác suất trung bình 0.27 so với 0.265 thật), hoặc model
   balanced đã prior-correct. Kiểm chứng: so tổng xác suất với số churn thật theo từng tháng trên dữ liệu
   gần nhất (backtest), reliability theo phân khúc (hợp đồng, vùng), và theo dõi theo thời gian vì tỉ lệ churn
   thay đổi theo mùa và theo chính sách giá.

## Sai lầm hay gặp

- Calibrate trên chính tập train: model đã quá tự tin trên dữ liệu nó thấy.
- Resample/SMOTE trước khi chia train/test: test không còn tỉ lệ thật, mọi metric sai.
- Calibrate theo phản xạ một model đã calibrated: tốn dữ liệu, có khi tệ đi.
