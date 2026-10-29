# Lời giải: so sánh model kinh điển trên bài review xấu của Olist

Notebook lời giải: `models.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Dữ liệu

95 824 đơn giao xong, có review và item, mua trước 2018-09-01; 12.8% review xấu.

| Tập | Số đơn | Review xấu | Giao trễ | Review xấu khi trễ |
| --- | --- | --- | --- | --- |
| train (trước 2018-01-01) | 43 362 | 12.1% | 6.5% | 54.6% |
| validation (Q1/2018) | 20 468 | 18.0% | 14.4% | 63.3% |
| test (04–08/2018) | 31 994 | 10.4% | 5.9% | 38.9% |

Ba tập khác nhau rõ: quý 1/2018 có nhiều đơn trễ (và đơn trễ dễ nhận ra), tháng 4–8 thì ít trễ hơn và đơn trễ
cũng ít bị review xấu hơn.

## So sánh model (validation)

| Model | ROC-AUC | PR-AUC | Log loss | Brier | Train ROC-AUC |
| --- | --- | --- | --- | --- | --- |
| random_forest | 0.806 | 0.611 | 0.343 | 0.099 | 0.918 |
| knn_50 | 0.794 | 0.594 | 0.413 | 0.103 | 0.772 |
| tree_depth5 | 0.808 | 0.591 | 0.351 | 0.099 | 0.724 |
| logistic | 0.798 | 0.569 | 0.375 | 0.113 | 0.711 |
| tree_full | 0.648 | 0.283 | 7.222 | 0.209 | 1.000 |

- Cây đầy đủ: variance thuần tuý, và log loss bùng nổ vì xác suất 0/1.
- Bốn model còn lại cách nhau rất ít. PR-AUC của đoán bừa trên validation là 0.18, nên 0.6 là tốt hơn
  nhiều so với ngẫu nhiên.
- Logistic có validation cao hơn train vì validation "dễ" hơn (nhiều đơn trễ), không phải vì model tốt lên.

## Validation so với test

Random forest: ROC-AUC 0.806 → 0.686, PR-AUC 0.611 → 0.337, Brier 0.099 → 0.081 (Brier giảm vì tỉ lệ dương
giảm, không phải vì model tốt hơn: Brier cũng phụ thuộc tỉ lệ nền). Nguyên nhân: mix shift. Tín hiệu mạnh nhất
(`late_days`) xuất hiện ít hơn ở test và yếu hơn khi xuất hiện.

## Ngưỡng theo chi phí (test)

| Ngưỡng | Chi phí mỗi đơn (R$) | Tỉ lệ liên hệ |
| --- | --- | --- |
| Không liên hệ ai | 3.114 | 0% |
| 0.5 | 2.627 | 2.8% |
| 5/35 = 0.143 | 2.279 | 15.2% |
| Chọn trên validation (0.175) | 2.263 | 10.7% |

## Trả lời câu hỏi

1. Cho đội CSKH: chi phí kỳ vọng mỗi đơn (hoặc tiết kiệm so với không làm gì) tại ngưỡng đã chọn, kèm precision
   (trong số đơn được gọi, bao nhiêu thật sự có vấn đề). PR-AUC là metric tốt để so model, không phải để báo cáo.
2. Lần này ngưỡng chọn trên validation (0.175, chi phí test 2.263 R$) gần ngưỡng tối ưu nhìn trộm trên test
   (0.179, 2.254 R$), vì xác suất của random forest gần calibrated ở cả hai (dự đoán trung bình 16.8% so với 18.0% thật ở validation, 11.1% so với 10.4% ở test). Production: train
   lại trên dữ liệu gần nhất, theo dõi calibration theo tháng, và khi năng lực CSKH cố định thì chọn top N
   thay vì ngưỡng cố định.
3. Dự đoán trước khi giao phải bỏ `delivery_days` và `late_days`. Tín hiệu mạnh nhất biến mất, ROC-AUC sẽ giảm
   đáng kể; thay bằng feature dự báo trễ (khoảng cách seller–khách, lịch sử trễ của seller, mùa cao điểm), đó
   là một bài toán dự đoán trễ riêng.

## Rubric (phần phân tích, không chấm tự động)

| Tiêu chí | Đạt khi |
| --- | --- |
| Thấy drift | Nêu tỉ lệ trễ, tỉ lệ review xấu khác nhau giữa ba tập và hệ quả cho metric |
| Đọc overfitting đúng | Phân biệt cây đầy đủ (hỏng) với random forest (khoảng cách lớn nhưng tốt nhất) |
| Metric | Biết PR-AUC phải so với tỉ lệ dương; log loss phạt xác suất cực đoan |
| Ngưỡng | Chọn trên validation, chấm trên test, có baseline "không liên hệ ai" |
