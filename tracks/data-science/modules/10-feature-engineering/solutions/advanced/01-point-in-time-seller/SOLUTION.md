# Hướng làm: feature lịch sử seller point-in-time

## Hàm `seller_history`

Cách nhanh (O(n log n)):

1. Mỗi dòng có nhãn là một **event** `(seller_id, label_time, bad_review)`. Sắp event theo
   `label_time`, cộng dồn số event và số review xấu theo seller.
2. Mỗi dòng cũng là một **truy vấn** `(seller_id, prediction_time)`. `pd.merge_asof(queries, events,
   left_on="prediction_time", right_on="label_time", by="seller_id", allow_exact_matches=False)` lấy
   trạng thái cộng dồn của event cuối cùng **trước hẳn** lúc dự đoán.
3. Trừ nhãn của chính dòng nếu `label_time < prediction_time` (khoảng 4.9% đơn Olist có review trả
   lời trước cả lúc giao).
4. Làm trơn: `(bad + m·prior) / (n + m)`, trả về đúng thứ tự dòng ban đầu (giữ một cột vị trí).

Trên 95 824 đơn Olist, hàm chạy trong khoảng 0.04 giây. Brute force theo từng seller cho cùng kết quả
nhưng chậm theo bình phương số đơn của seller lớn nhất.

## Các quyết định thiết kế cần cân nhắc

- **Mốc "nhãn được biết".** `review_answer_timestamp` là lúc điểm số thật sự vào hệ thống.
  `review_creation_date` là lúc gửi khảo sát (00:00), sớm hơn, dùng nó là rò rỉ vài ngày.
- **So sánh chặt.** Event cùng thời điểm với dự đoán không được dùng. Ở production còn phải cộng độ
  trễ của pipeline (review mới vào feature store sau vài giờ), và tốt nhất là mô phỏng độ trễ đó khi
  tạo dữ liệu train.
- **Seller chưa có lịch sử** (2.0% đơn validation): nhận prior; thêm `log(1 + seller_past_reviews)`
  để model biết mức tin cậy.
- **Smoothing.** 20 là lựa chọn hợp lý cho tỉ lệ nền 12%; có thể chọn trên validation.
- **Cửa sổ thời gian.** Toàn bộ lịch sử hay 90 ngày gần nhất? Cửa sổ ngắn bắt được seller xấu đi
  nhanh hơn nhưng nhiễu hơn. Một lựa chọn bảo vệ được là cả hai.
- **Prior lấy từ train**, không lấy từ toàn bộ dữ liệu.

## Kết quả tham khảo (model logistic của Intermediate 02)

| Biến thể | AUC val | AUC test |
| --- | --- | --- |
| Không có seller | 0.7985 | 0.6949 |
| Target encoding `seller_id` (OOF) | 0.8011 | 0.6998 |
| Tỉ lệ seller trên toàn bộ dữ liệu (SAI) | 0.8240 | 0.7592 |
| Lịch sử seller point-in-time | 0.8044 | 0.7106 |

Biến thể sai đứng đầu cả hai cột vì nó đã thấy nhãn của chính các đơn validation và test: 0.759
trên test là con số không hệ thống nào đạt được khi chạy thật. Trong các biến thể trung thực, lịch sử
point-in-time tốt nhất, nhất là trên test (+0.011 so với target encoding): nó tiếp tục cập nhật trong
giai đoạn test, còn target encoding đóng băng ở dữ liệu train.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm đúng và nhanh | 25 | Test pass: so sánh chặt, loại nhãn của chính đơn, khớp brute force, 100 nghìn dòng dưới 5 giây |
| Giải thích leakage | 15 | Chỉ ra cả hai đường rò: tương lai và nhãn của chính đơn; giải thích vì sao AUC một mình của feature sai không cao bất thường mà vẫn là leakage |
| Định nghĩa point-in-time | 15 | Nêu rõ mốc nào so với mốc nào, vì sao chọn `review_answer_timestamp`, xử lý seller mới và smoothing |
| Đọc bảng kết quả | 20 | Nhận ra biến thể sai đứng đầu vì rò rỉ; so sánh các biến thể trung thực trên cả val và test; không kết luận từ chênh lệch nhỏ mà không nêu độ bất định |
| Production | 15 | As-of join từ feature store, cùng một logic cho train và serve, độ trễ cập nhật, training-serving skew |
| Kiểm tra tự động | 10 | Đề xuất kiểm tra trước mỗi lần retrain (so với brute force trên mẫu, AUC một mình, `available_after`) |

Đạt từ 70 điểm: feature đủ an toàn để đưa vào model production sau một lượt review.
