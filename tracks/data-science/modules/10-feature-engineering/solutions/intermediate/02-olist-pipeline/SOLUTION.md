# Lời giải: Pipeline cho bài toán review xấu

Notebook lời giải: `pipeline.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Cột leakage

Mọi cột sinh ra từ review: `review_id`, `review_score`, `review_comment_title`,
`review_comment_message`, `review_creation_date`, `review_answer_timestamp`, và chính nhãn
`bad_review`. Ở thời điểm dự đoán (đơn vừa giao), review chưa tồn tại với hơn 90% đơn.

Không phải leakage dù trông giống: `order_delivered_customer_date` và các feature suy ra (`delay_days`,
`delivery_days`) hợp lệ **vì** ta dự đoán lúc giao xong. Nếu đổi bài toán thành dự đoán lúc mua thì
chúng trở thành leakage. Leakage là quan hệ giữa feature và **thời điểm dự đoán**, không phải tính
chất của riêng cột.

## Chọn feature

17 cột số (thời gian, đơn hàng, sản phẩm, khoảng cách), 4 cột phân loại ít giá trị (bang khách, bang
seller, phương thức thanh toán, danh mục sản phẩm), `seller_id` (2 956 seller trên toàn bảng) cho
target encoding. Không dùng id thuần (`order_id`, `customer_id`): mỗi giá trị chỉ xuất hiện một lần,
không mang thông tin tổng quát hoá được. `customer_unique_id` có lặp nhưng rất ít (bài Intermediate 03).

## Pipeline

```text
ColumnTransformer
├── num: SimpleImputer(median) → StandardScaler          17 cột
├── cat: SimpleImputer("missing") → OneHotEncoder(infrequent_if_exist, min_frequency=20)
└── te:  TargetEncoder(cv=KFold(5, shuffle=True))         seller_id
→ LogisticRegression(C, max_iter=2000)
```

- Gói mọi bước học tham số (median, mean/std, danh sách category, bảng target encoding) **vào trong**
  pipeline: `fit` trên train là đủ để không bước nào nhìn validation. Đây là điều test
  `test_fit_uses_train_only` kiểm: làm lệch validation không làm đổi model.
- `handle_unknown="infrequent_if_exist"` + `min_frequency`: danh mục hiếm và danh mục lạ dùng chung
  một cột, model không vỡ khi có giá trị mới.
- Không dùng `remainder="passthrough"`: nó sẽ đưa mọi cột còn lại (kể cả `review_score`) vào model.

## Kết quả

| Biến thể | AUC validation |
| --- | --- |
| Đầy đủ (lời giải) | 0.8011 |
| Bỏ `seller_id` | 0.7985 |
| Thêm `comment_len` (leakage) | 0.8762 |

AUC test (fit lại trên train + val, đo một lần): **0.6998**. Chênh với validation không phải do
overfit mà do phân phối: tỉ lệ giao trễ 14.4% ở validation, 5.9% ở test. Giao hàng là tín hiệu
mạnh nhất; khi ít đơn trễ, model khó phân biệt hơn.

Hệ số lớn nhất là của `seller_id` sau target encoding và vài bang, danh mục. Đọc hệ số one-hot cẩn
thận: chúng tương đối so với cột bị gộp/bị bỏ, và có thang khác với cột số đã scale.

## Sai lầm hay gặp

- `StandardScaler().fit(table)` rồi mới chia train/val: rò rỉ trung bình và độ lệch chuẩn của
  validation vào train. Với logistic hiệu ứng nhỏ, nhưng với imputer, target encoding hay chọn
  feature thì lớn.
- `pd.get_dummies` riêng trên train và val: cột lệch nhau khi val có danh mục mới hoặc thiếu danh mục.
- Tối ưu `C` hay chọn feature bằng test: test không còn là ước lượng không chệch nữa.
