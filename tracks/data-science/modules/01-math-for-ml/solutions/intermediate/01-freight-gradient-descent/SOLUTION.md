# Lời giải: gradient descent và learning rate schedule cho phí ship Olist

Notebook lời giải: `freight_gd.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Bảng dữ liệu

Ghép `order_items` → `products` (khối lượng, kích thước) → `orders` (thời điểm mua), bỏ item thiếu
kích thước, bỏ đơn mua từ 2018-09-01, gán split theo quy ước chung của track. Kết quả: 51 216 item
train, 24 097 val, 37 318 test. Chia theo thời gian, không chia ngẫu nhiên: model phí ship sẽ được
dùng cho đơn **tương lai**, và giá cước đổi theo thời gian.

## Gradient descent và schedule

`gradient_descent` giữ residual `r = Xw − y` để tính cả loss lẫn gradient $$\frac{2}{n}X^\top r$$ trong cùng
một lượt. Bước thứ `t` gọi `lr_at(t, ...)`; test `step` với `decay = 0` kiểm rằng schedule thật sự
được dùng (sau `step_size` bước, lr = 0 và loss đứng yên).

## Kết quả trên Olist thật

| | κ(H) | lr tối đa 2/L | Số bước tới loss cách tối ưu 1e-6 (lr = 1/L) |
| --- | --- | --- | --- |
| Đơn vị gốc (kg, lít) | 1 328.6 | 0.00108 | 9 231 |
| Feature chuẩn hoá | 8.6 | 0.558 | 30 |

Cùng bài toán, cùng nghiệm, nhanh hơn khoảng 300 lần chỉ nhờ chuẩn hoá. Lý do: gradient descent
tiến nhanh theo hướng cong nhiều và rất chậm theo hướng cong ít; số bước tỉ lệ với $$\kappa$$. Trên
đơn vị gốc, cột intercept (giá trị 1) và cột thể tích (trung bình 16.5 lít, độ lệch chuẩn 25.3 trên train) có thang
đo chênh nhau, nên mặt loss là một "thung lũng" hẹp và dài.

Quanh ngưỡng 2/L (feature chuẩn hoá, 100 bước):

| Cấu hình | Loss sau 100 bước |
| --- | --- |
| 0.9 · 2/L, constant | 111.9 (hội tụ, dao động dấu ở hướng cong nhất) |
| 1.1 · 2/L, constant | 6.5 · 10¹⁷ (phân kỳ) |
| 1.1 · 2/L, inverse_time (decay 0.05) | 111.9 (loss nhích lên 267 → 275 ở bước 2 rồi hội tụ) |
| 0.1 · 2/L, constant | 111.9 |

Hệ số sau khi đổi về đơn vị gốc: 13.2485 + 1.4592 · kg + 0.1790 · lít, trùng normal equation (Basic 02).
Test RMSE 14.87 so với 18.40 của dự đoán hằng; R² test 0.342.

## Vì sao học gradient descent khi đã có normal equation

Với 2 feature thì không cần: normal equation nhanh và chính xác hơn. Gradient descent đáng giá khi
(1) loss không có nghiệm đóng (logistic regression, mạng nơ-ron), (2) d quá lớn cho $$O(d^3)$$, (3) dữ
liệu đến theo dòng (online learning). Bài này dùng linear regression vì có đáp án chính xác để kiểm.

## Sai lầm hay gặp

- Chuẩn hoá bằng `mu`, `sd` tính trên **cả** train và test: rò rỉ thông tin. Fit trên train, áp cho
  val/test.
- Quên đổi hệ số về đơn vị gốc rồi báo cáo "mỗi kg thêm 5.7 BRL" (đó là mỗi độ lệch chuẩn).
- Chọn lr bằng thử–sai trên đơn vị gốc, thấy phải dùng 0.0005 và kết luận "gradient descent chậm".
  Vấn đề là condition number, không phải thuật toán.
- Tin rằng schedule cứu được mọi lr0: với `step` có `step_size` dài, lr0 quá lớn làm loss nổ thành
  `inf` trước khi lr kịp giảm.
