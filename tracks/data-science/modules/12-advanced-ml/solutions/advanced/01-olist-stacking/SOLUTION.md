# Hướng làm: stacking theo thời gian cho Olist

Bài Advanced không có đáp án duy nhất. Dưới đây là cài đặt tham chiếu cho các hàm được chấm, kết quả
tham chiếu trên dữ liệu thật, và rubric.

## Các hàm được chấm

- `expanding_folds`: `pos = np.argsort(order, kind="stable")`, `blocks = np.array_split(pos, n_folds + 1)`,
  fold k là `(concat(blocks[:k + 1]), blocks[k + 1])`.
- `oof_predictions`: DataFrame NaN cùng index với `X`; mỗi fold, mỗi model: `factory().fit(...)`,
  ghi `predict_proba(...)[:, 1]` bằng `iloc`.
- `to_logit`: `np.clip(P, eps, 1 - eps)` rồi $$\log\frac{p}{1-p}$$.
- `fit_meta`: `LogisticRegression(max_iter=1000)` trên các dòng OOF không NaN.

Vì sao không dùng `sklearn.ensemble.StackingClassifier` với `cv=TimeSeriesSplit`: sklearn yêu cầu
`cv` cho dự đoán trên **mọi** dòng (một phân hoạch), trong khi fold theo thời gian để khối đầu không
có OOF. Tự viết vài dòng cho phép kiểm soát chính xác điều đó.

## Kết quả tham chiếu trên Olist thật

Ba model tầng 1: logistic regression (one-hot + chuẩn hoá), LightGBM 120 cây, random forest 200 cây
(`min_samples_leaf=30`, `max_features=0.3`). Dev 63 830 đơn, 4 fold mở rộng; test 31 994 đơn.

| | AUC test | PR-AUC test | Log loss test |
| --- | --- | --- | --- |
| Logistic | 0.7101 | 0.3057 | 0.2978 |
| LightGBM | 0.7139 | 0.3518 | 0.2892 |
| Random forest | 0.7055 | 0.3470 | 0.2906 |
| Trung bình đơn giản 3 model | 0.7153 | 0.3509 | 0.2893 |
| Stacking (meta logistic) | 0.7126 | 0.3519 | 0.2908 |

- Tương quan OOF: LightGBM và random forest 0.979, logistic với hai model cây khoảng 0.89–0.90. Các
  model "đồng ý" với nhau gần như hoàn toàn, nên kết hợp không có nhiều thứ để thêm.
- Hệ số meta-model: logistic 0.07, LightGBM 0.48, random forest 0.58.
- Chênh lệch AUC stacking trừ LightGBM: −0.0012, bootstrap 300 lần trên test cho CI 95% khoảng
  [−0.0042, +0.0017]. **Không phân biệt được với 0.**
- Thời gian: OOF 4 fold × 3 model mất khoảng 4 phút trên một luồng CPU (random forest chiếm phần
  lớn), so với vài giây cho một LightGBM.

Khuyến nghị mạnh nhất từ số liệu: **không** đưa stacking vào production cho bài này. Dùng LightGBM
đơn; nếu muốn kết hợp, trung bình đơn giản hai model khác bản chất là đủ và không cần meta-model.
Cải thiện tiếp theo nên đến từ feature (lịch sử seller, khoảng cách giao hàng, văn bản mô tả sản
phẩm) và từ việc xử lý distribution shift của quý 1/2018, không từ thêm model.

## Các quyết định thiết kế cần cân nhắc

- **Fold**: expanding window khớp cách model được dùng (học quá khứ, dự đoán tương lai). Sliding
  window nếu dữ liệu cũ không còn đại diện. KFold ngẫu nhiên cho OOF lạc quan và meta-model học sai
  trọng số.
- **Meta-model**: tuyến tính trên logit là mặc định. LightGBM làm meta-model chỉ khi có rất nhiều
  dòng OOF và lý do tin rằng trọng số nên thay đổi theo feature (khi đó đưa thêm vài feature gốc vào
  meta-model).
- **Blending** (meta-model học trên một tập holdout cố định) đơn giản hơn stacking OOF, tốn dữ liệu
  hơn. Với Olist, holdout quý 1/2018 lại là giai đoạn bất thường: meta-model học trên đó sẽ ưu tiên
  model bắt được "trễ" tốt nhất.
- **Chi phí**: N model phải train, version, giám sát drift và retrain cùng nhịp; một model tầng 1
  hỏng (feature pipeline đổi) làm hỏng cả hệ, khó debug. Latency cộng dồn nếu chạy tuần tự.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm được chấm đúng (test pass) | 20 | 8/8 test pass |
| Đa dạng model tầng 1 | 10 | ≥ 3 model khác bản chất, có lý do chọn; xem tương quan OOF |
| Đánh giá đúng | 20 | Test không dùng để tune; meta-model học trên OOF; model tầng 1 fit lại trên dev trước khi dự đoán test |
| Độ không chắc chắn | 15 | Bootstrap (hoặc tương đương) cho chênh lệch, đọc đúng CI chứa 0 |
| Chi phí vận hành | 15 | Lượng hoá thời gian train/dự đoán, nêu rủi ro giám sát và retrain |
| Khuyến nghị | 15 | Kết luận rõ ở câu đầu, khớp số liệu, có bước tiếp theo cụ thể |
| Trình bày | 5 | Người đọc không chuyên về ensemble vẫn hiểu |

Đạt từ 70 điểm. Lỗi trừ nặng: kết luận "stacking tốt hơn" dựa trên chênh lệch nằm trong nhiễu;
OOF bằng KFold ngẫu nhiên; meta-model học trên chính dự đoán in-sample.
