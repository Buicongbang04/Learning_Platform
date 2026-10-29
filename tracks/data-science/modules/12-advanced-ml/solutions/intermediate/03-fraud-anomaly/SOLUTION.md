# Lời giải: anomaly detection trên gian lận thẻ

Notebook lời giải: `fraud.ipynb` (chạy được toàn bộ khi đã tải `creditcard-fraud`).

## Cách làm

- **AP**: sort điểm giảm dần (`kind="stable"`), cộng dồn số dương tính, chỉ giữ vị trí cuối của
  mỗi nhóm điểm bằng nhau, rồi $$\sum (R_n - R_{n-1}) P_n$$. Nếu không gộp nhóm bằng nhau, kết quả phụ
  thuộc thứ tự dòng trong dữ liệu: một dương tính đứng trước các âm tính cùng điểm sẽ được "thưởng"
  một precision không có thật.
- **Isolation forest**: `-IsolationForest(...).fit(X_train).score_samples(X_test)`.
- **PCA reconstruction**: chuẩn hoá theo train, PCA fit trên train, sai số dựng lại trên test. Đây là
  autoencoder tuyến tính một lớp ẩn: encoder là phép chiếu xuống 15 thành phần, decoder là phép
  chiếu ngược.

## Kết quả trên ngày thứ hai (140 021 giao dịch, 211 gian lận, 0.151%)

| Bộ chấm điểm | ROC-AUC | AP | precision@100 | recall@500 |
| --- | --- | --- | --- | --- |
| Ngẫu nhiên | 0.489 | 0.001 | 0.00 | 0.000 |
| Số tiền càng nhỏ càng nghi | 0.561 | 0.004 | 0.05 | 0.043 |
| Isolation forest | 0.956 | 0.130 | 0.26 | 0.299 |
| PCA, học trên mọi giao dịch train | 0.927 | 0.041 | 0.08 | 0.123 |
| PCA, học trên giao dịch sạch | 0.971 | 0.209 | 0.38 | 0.526 |

AP của isolation forest theo 5 seed: 0.101–0.149. Bộ phát hiện không nhãn dao động khá nhiều; báo
cáo khoảng, không báo một seed.

Đọc bảng:

- ROC-AUC của mọi phương pháp không nhãn đều trên 0.92, nhưng AP chỉ 0.04–0.21. Lớp âm có 140 nghìn
  dòng, nên FPR 1% đã là khoảng 1 400 báo động sai mỗi ngày.
- Ngân sách 500 cảnh báo mỗi ngày: PCA sạch bắt được 53% gian lận, isolation forest 30%. Đây là con
  số đội vận hành quan tâm.
- Trung vị số tiền gian lận là 9.25 so với 22.00 của giao dịch thường, nhưng dùng "số tiền nhỏ"
  làm điểm gần như vô dụng (AP 0.004): một feature khác biệt về trung vị không có nghĩa là phân
  biệt được.

## Ba câu hỏi

Câu trả lời đầy đủ ở cell cuối notebook lời giải. Ý chính: báo cáo precision/recall theo ngân sách
cảnh báo cùng AP; contamination làm PCA học luôn "hình dạng" của gian lận nên AP rơi từ 0.209 xuống
0.041; có nhãn thì supervised mạnh hơn nhiều, anomaly detection vẫn dùng cho kiểu gian lận mới, làm
feature và giám sát drift.

## Rubric cho phần nhận xét

| Tiêu chí | Đạt khi |
| --- | --- |
| ROC-AUC vs PR | Giải thích bằng số báo động sai tuyệt đối, không chỉ nói "mất cân bằng" |
| Metric cho vận hành | Đề xuất precision/recall tại ngân sách cảnh báo |
| Contamination | Giải thích cơ chế, nêu cách lấy dữ liệu "sạch" trong thực tế |
| Vai trò của anomaly detection khi có nhãn | Ít nhất hai vai trò hợp lý |

## Lỗi hay gặp

- Quên đổi dấu `score_samples`: AP của isolation forest gần 0, ROC-AUC dưới 0.5.
- Fit scaler hoặc PCA trên test (hoặc train + test): điểm của một giao dịch phụ thuộc giao dịch khác
  trong batch, và không làm được khi chấm từng giao dịch theo thời gian thực.
- Chia ngẫu nhiên thay vì theo thời gian: các giao dịch gian lận cùng một đợt tấn công rơi vào cả
  train và test, kết quả lạc quan.
- Chọn `contamination` của `IsolationForest` rồi dùng `predict` (−1/1): mất thứ hạng, chỉ còn một
  ngưỡng do thuật toán đặt. Hãy dùng điểm liên tục và tự chọn ngưỡng theo ngân sách.
