# Lời giải: LightGBM với early stopping trên Olist

Notebook lời giải: `lgbm_olist.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Cách làm

- `fit_early_stopping`: copy `params` (hoặc `PARAMS`), ép `metric="binary_logloss"`, tạo
  `lgb.Dataset` cho validation với `reference=train_set`, gọi `lgb.train` với callback
  `lgb.early_stopping(patience, verbose=False)` và **chỉ** validation trong `valid_sets`.
- `evaluate`: `booster.predict(X, num_iteration=booster.best_iteration)` rồi tính AUC, PR-AUC
  (average precision), log loss.
- `lr_sweep`: lặp qua `rates`, ghi `best_iteration` và metric.

Vì sao theo dõi logloss thay vì AUC: logloss mượt hơn và đo cả chất lượng xác suất. AUC chỉ đo thứ
hạng, thường "phẳng" rất lâu nên early stopping theo AUC dừng muộn và dao động. Nếu sản phẩm cuối
dùng xác suất (chọn ngưỡng theo chi phí, module 11), logloss là thước đo đúng.

## Kết quả trên Olist thật

| | Train | Validation | Test |
| --- | --- | --- | --- |
| Số đơn | 43 362 | 20 468 | 31 994 |
| Tỉ lệ review xấu | 12.1% | 18.0% | 10.4% |

- Early stopping (lr 0.05, patience 50): `best_iteration` 117. AUC validation 0.820, test 0.707;
  PR-AUC test 0.347 (tỉ lệ nền 0.104); logloss test 0.290.
- Cùng tham số, train đủ 1 000 cây không dừng: test AUC 0.689, logloss 0.305. Early stopping
  vừa tốt hơn vừa nhỏ gấp gần 9 lần.

| learning_rate | best_iteration | logloss validation | AUC test |
| --- | --- | --- | --- |
| 0.20 | 16 | 0.3388 | 0.699 |
| 0.10 | 44 | 0.3367 | 0.708 |
| 0.05 | 117 | 0.3362 | 0.707 |
| 0.02 | 261 | 0.3359 | 0.707 |

Số cây gần như tỉ lệ nghịch với learning rate. Từ 0.05 trở xuống, chất lượng không đổi đáng kể
nhưng số cây (thời gian train và độ trễ khi dự đoán) tăng. Thực tế: thử nhanh với 0.1, chốt với
0.05 hoặc 0.02 khi tham số khác đã ổn.

Feature quan trọng nhất theo gain: `days_vs_estimate` (37%), `delivery_days` (10%), `n_items`
(8%), `is_late` (7%), `product_category_name` (6%). Gain đo "model dùng feature nhiều", không đo
tác động nhân quả, và bị thổi phồng với feature có nhiều giá trị khác nhau; module 11 dùng SHAP và
permutation importance cho câu hỏi giải thích.

## Ba câu hỏi

Câu trả lời đầy đủ nằm trong cell cuối của notebook lời giải. Tóm tắt:

1. Quý 1/2018 trễ nặng (21.1% đơn trễ trong tháng 3), review xấu 18%: validation dễ hơn test. Vẫn
   dùng để chọn số cây được, nhưng báo cáo hiệu năng bằng test.
2. Train lại trên train + validation với 117 cây: test AUC 0.714. Không dùng test để chọn.
3. Can thiệp trước khi giao cần một điểm dự đoán khác (lúc mua hoặc lúc giao cho hãng vận chuyển)
   và phải bỏ mọi kết quả giao hàng xảy ra sau điểm đó. Chỉ bỏ ba feature hậu giao hàng: test AUC
   0.656, PR-AUC 0.238. Chọn model theo thời điểm cần ra quyết định.

## Rubric cho phần câu hỏi

| Tiêu chí | Đạt khi |
| --- | --- |
| Distribution shift | Chỉ ra quý 1/2018 trễ bất thường, không kết luận "model overfit test" |
| Refit | Có lập luận về số cây khi thêm dữ liệu, không chạm test |
| Thời điểm dự đoán | Liệt kê đúng feature hậu giao hàng, nói được đánh đổi sớm/chính xác |

## Lỗi hay gặp

- Đưa test vào `valid_sets` "để xem cho tiện": callback early stopping theo dõi **mọi** tập trong
  `valid_sets` và dừng khi một tập bất kỳ ngừng cải thiện, nên test tham gia chọn số cây và con số
  test không còn khách quan.
- Quên `reference=train_set` khi tự tạo `lgb.Dataset` cho validation: bin của validation có thể
  không khớp bin của train.
- So sánh hai learning rate với cùng số cây cố định: kết luận "lr nhỏ tệ hơn" chỉ vì chưa đủ cây.
- Dùng KFold ngẫu nhiên cho early stopping trên dữ liệu thời gian: số cây được chọn lạc quan
  (module 10).
