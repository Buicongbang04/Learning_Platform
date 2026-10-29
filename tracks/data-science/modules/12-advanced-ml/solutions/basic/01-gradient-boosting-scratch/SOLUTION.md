# Lời giải: tự viết gradient boosting

## Cách làm

Gradient boosting là gradient descent trong **không gian hàm**. Mỗi vòng ta muốn đi một bước
ngược hướng gradient của loss theo dự đoán $$F(x_i)$$; nhưng gradient chỉ biết ở các điểm train,
nên ta fit một cây $$h_m$$ để xấp xỉ negative gradient, rồi cộng $$\nu h_m$$ vào mô hình:

$$
r_i = -\frac{\partial L(y_i, F)}{\partial F}\Big|_{F = F_{m-1}(x_i)}, \qquad
F_m = F_{m-1} + \nu\, h_m
$$

- Squared loss: $$r_i = y_i - F_{m-1}(x_i)$$, chính là phần dư. Giá trị lá của cây hồi quy (trung bình
  phần dư trong lá) đã là tối ưu, không cần sửa. Vì vậy lời giải trùng sklearn tới sai số máy.
- Absolute loss: $$r_i = \operatorname{sign}(y_i - F)$$. Cây chỉ học được **hướng**; độ lớn bước đi trong
  mỗi lá được chọn lại bằng median phần dư, giá trị tối ưu của MAE trong lá đó.

`staged_loss` cộng dồn từng cây nên tốn O(M) lần `predict` thay vì O(M²).

## Số liệu từ test

- Loss train của squared giảm đơn điệu, sau 80 cây depth 2 còn dưới 7% phương sai ban đầu (30
  seed thử, lớn nhất 6.6%). Loss train giảm mãi không có nghĩa mô hình tốt hơn: với nhiễu
  $$\sigma = 0.3$$ (phương sai 0.09), MSE train xuống dưới 0.09 là đang học thuộc nhiễu.
- 8% outlier cỡ ±20–40: MAE trên dữ liệu sạch của absolute loss chỉ bằng 11–25% của squared loss
  (30 seed). Squared loss bị outlier kéo cả $$F_0$$ lẫn từng lá.

## Câu hỏi thêm: holdout bắt đầu xấu đi khi nào

Dữ liệu `make_data(n=400, seed=0)` của test, holdout 2 000 điểm `seed=1`, cây depth 3, 500 vòng:

| learning_rate | Số cây tốt nhất trên holdout | MSE holdout tốt nhất | MSE holdout ở 500 cây | MSE train ở 500 cây |
| --- | --- | --- | --- | --- |
| 0.5 | 29 | 0.128 | 0.148 | 0.000 |
| 0.05 | 166 | 0.109 | 0.117 | 0.017 |

Learning rate nhỏ cần nhiều cây hơn (gấp khoảng 6 lần), nhưng điểm tốt nhất **tốt hơn** và vùng
quanh điểm tốt nhất **phẳng hơn**, nên chọn sai số cây ít bị phạt. Đó là lý do công thức thực tế là
"learning rate nhỏ + early stopping" (mục 3 lý thuyết).

## Khi nào dùng loss nào

| Loss | Dùng khi | Đánh đổi |
| --- | --- | --- |
| Squared | Mặc định, nhiễu gần chuẩn, cần dự đoán trung bình | Nhạy outlier |
| Absolute | Có outlier, cần dự đoán median (thời gian giao hàng, giá) | Hội tụ chậm hơn, gradient không mang thông tin độ lớn |
| Huber | Muốn cả hai: bậc hai gần 0, tuyến tính ở xa | Thêm tham số ngưỡng |
| Quantile | Dự đoán khoảng (P90 thời gian giao) | Mỗi quantile một mô hình |

## Lỗi hay gặp

- Quên `learning_rate` khi dự đoán (cộng `tree.predict` không nhân $$\nu$$) hoặc nhân cả $$F_0$$.
- Absolute loss mà không sửa lá: mô hình vẫn chạy nhưng hội tụ rất chậm, vì mỗi bước tối đa ±ν.
- Ghi `tree.tree_.value[leaf]` bằng chỉ số sai: `tree.apply` trả **id node** (đúng chỉ số trong
  `tree_.value`), không phải thứ tự lá 0, 1, 2…
