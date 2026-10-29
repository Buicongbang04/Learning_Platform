# Hướng làm: feature selection bên trong cross-validation

## Ba hàm

- `leaky_selection_auc`: `SelectKBest(f_classif, k).fit(X, y)` trên **toàn bộ** dữ liệu, giữ cột được
  chọn, rồi `cross_val_score(LogisticRegression(max_iter=1000), X_sel, y, cv=cv, scoring="roc_auc")`.
- `honest_selection_auc`: `make_pipeline(SelectKBest(f_classif, k), LogisticRegression(max_iter=1000))`
  rồi `cross_val_score` trên toàn bộ X: bộ chọn được fit lại trong từng fold.
- `selection_frequency`: với mỗi `(train_idx, _)`, fit bộ chọn trên phần train, cộng `get_support()`,
  chia cho số fold. Chuyển `splits` thành `list` trước (có thể là generator).

## Mô phỏng (12 seed)

| Dữ liệu | Chọn ngoài CV | Chọn trong CV |
| --- | --- | --- |
| 200 dòng, 2 000 feature nhiễu, nhãn ngẫu nhiên, k = 20 | 0.82–0.91 | 0.41–0.66 |
| 1 000 dòng, 5 feature thật trong 200, k = 5 | 0.82–0.87 | bằng cột bên trái |

Khi có tín hiệu thật, hai cách cho cùng kết quả; khi không có, cách sai bịa ra AUC 0.85. Chênh lệch
giữa hai cách chính là lượng leakage. Đây là ví dụ kinh điển trong *The Elements of Statistical
Learning* (mục 7.10.2) về cách làm sai cross-validation.

## Olist (pipeline của Intermediate 02, AUC validation 0.8011)

Permutation importance trên validation (giảm AUC khi hoán vị, 5 lần):

| Feature | Giảm AUC |
| --- | --- |
| `delivery_days` | 0.0936 |
| `delay_days` | 0.0410 |
| `n_items` | 0.0217 |
| `n_sellers` | 0.0111 |
| `seller_id` | 0.0046 |
| `distance_km` | 0.0033 |
| `product_category_name`, `promised_days` | 0.0028 mỗi cột |
| `customer_state` | 0.0018 |
| 13 feature còn lại | dưới 0.001 |

Bỏ 13 feature dưới 0.001 (22 cột đầu vào còn 9): AUC validation 0.8027 (so với 0.8011), AUC test
0.6988 (so với 0.6998). Gần như không mất gì, pipeline đơn giản hơn nhiều: không cần bảng payments,
ít join lúc serving. Lưu ý: chọn feature bằng validation rồi đo trên chính validation hơi lạc quan;
con số test (đo một lần sau khi chốt) mới là con số báo cáo.

**Tương quan.** `delivery_days` và `delay_days` tương quan 0.74. Hoán vị riêng từng cột, tổng mức
giảm của ba feature giao hàng (`promised_days`, `delivery_days`, `delay_days`) là 0.137; hoán vị cả
nhóm cùng lúc làm AUC giảm 0.257. Mỗi cột "che" cho cột kia, nên importance từng cột đánh giá thấp
cả nhóm. Đừng bỏ hai feature tương quan cùng lúc chỉ vì từng cái trông yếu.

## Các quyết định cần cân nhắc

- Công cụ chọn: permutation importance (theo metric thật, trên dữ liệu chưa thấy), L1 (nhanh, nhưng
  phụ thuộc scale và chọn ngẫu nhiên một trong các feature tương quan), độ ổn định qua fold thời gian.
- Ngưỡng bỏ: theo importance tuyệt đối, theo độ ổn định, hay theo chi phí tính feature lúc serving
  (feature cần join bảng lớn đắt hơn feature có sẵn trong đơn).
- Feature yếu hôm nay có thể quan trọng khi phân phối đổi (ví dụ mùa cao điểm): giữ danh sách và
  đánh giá lại mỗi lần retrain.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Ba hàm đúng | 20 | Test pass; bộ chọn chỉ học trên phần train của fold |
| Giải thích mô phỏng | 15 | Giải thích được cơ chế cho người không làm ML; nối với leakage của target encoding hay scaler |
| Phân tích Olist | 25 | Importance đo trên validation theo thời gian, có lặp lại; nhận ra tác động của tương quan (hoán vị theo nhóm hoặc tương đương) |
| Đề xuất có bằng chứng | 20 | So AUC trước/sau, nêu cái được (đơn giản, chi phí serving) và cái mất; test chỉ đo một lần ở cuối |
| Rủi ro và theo dõi | 20 | Drift làm feature yếu thành mạnh; kế hoạch theo dõi; không dùng KFold ngẫu nhiên để đánh giá việc rút gọn |

Đạt từ 70 điểm: đề xuất đủ thuyết phục để lead DS duyệt.
