# Lời giải: hai phép kiểm nhanh phát hiện leakage

Tệp lời giải: `leak_check.py`.

## Cách làm

- `single_feature_auc`: AUC không đổi khi biến đổi đơn điệu feature, nên không cần scale hay chọn
  ngưỡng. Lấy `max(AUC, 1 − AUC)` vì feature tương quan âm cũng là tín hiệu mạnh. Bỏ NaN theo từng
  cột, và trả 0.5 khi không tính được (cột hằng, một lớp).
- `available_after`: câu hỏi đúng không phải "giá trị có phải ngày tương lai không" mà là "giá trị
  được **ghi nhận** lúc nào". Vì vậy hàm nhận `known_at`: mỗi feature trỏ tới cột thời điểm ghi nhận
  của nó. Ngày hẹn giao có giá trị muộn hơn ngày giao ở 92.0% đơn, nhưng được ghi nhận lúc mua, nên
  hoàn toàn hợp lệ.

## Kết quả trên Olist thật (dự đoán lúc giao xong)

| Feature | Ghi nhận lúc | Sau lúc dự đoán |
| --- | --- | --- |
| `review_score` | `review_answer_timestamp` | 95.1% |
| `review_comment_message` | `review_creation_date` | 91.5% |
| `order_estimated_delivery_date` | `order_purchase_timestamp` | 0% |
| `order_approved_at` | chính nó | 0.06% (lỗi dữ liệu: duyệt sau khi đã giao) |

| Feature | AUC một mình |
| --- | --- |
| `comment_len` (độ dài bình luận review) | 0.756 |
| `delivery_days` | 0.685 |
| `delay_days` | 0.657 |

`comment_len` mạnh hơn mọi feature giao hàng: khách bực thì viết dài. Nó rò rỉ vì bình luận là một
phần của chính review. Còn 4.9% đơn có review trả lời *trước* lúc giao: với những đơn đó nhãn đã biết
lúc dự đoán, nhưng vẫn không được dùng làm feature vì nó chính là thứ cần dự đoán.

## Vì sao đây chỉ là sàng lọc

- **Bỏ sót**: leakage yếu (ví dụ tỉ lệ review xấu của seller tính trên toàn bộ dữ liệu, AUC một mình
  khoảng 0.65) không bị ngưỡng 0.9 bắt, nhưng vẫn làm AUC validation tăng từ 0.80 lên 0.82 (bài Advanced 01).
- **Báo nhầm**: một feature hợp lệ có thể rất mạnh. Ngưỡng chỉ là tín hiệu để hỏi "cột này ghi
  nhận lúc nào, từ hệ thống nào".
- Với `available_after`, cái khó là **biết** cột thời điểm ghi nhận. Bảng dữ liệu thường chỉ có giá
  trị mới nhất (bị ghi đè), không có lịch sử. Đó là lý do feature store và bảng snapshot tồn tại.

## Sai lầm hay gặp

- Dùng `roc_auc_score` trực tiếp trên cột có NaN: lỗi, hoặc tệ hơn, `fillna(0)` làm NaN thành một
  "giá trị" mang tín hiệu (thiếu dữ liệu thường tương quan với nhãn).
- Kiểm leakage bằng cách nhìn feature importance của model đã train: chỉ thấy sau khi đã tốn công,
  và importance cao chưa chắc là leakage.
