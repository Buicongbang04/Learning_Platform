# Lời giải: PSI và KS

## Cách làm

**PSI.** Chia bin theo quantile của reference để mỗi bin có khoảng $$1/\text{bins}$$ dữ liệu
reference. Chia theo khoảng đều (`np.linspace(min, max)`) thì với biến lệch phải như `freight`
hay `delivery_days`, gần như mọi dữ liệu dồn vào hai ba bin đầu, PSI mất độ nhạy ở phần thân và
quá nhạy ở đuôi. Ba chi tiết dễ sai:

- **Biên ngoài cùng là vô cực.** Nếu giữ biên min/max của reference thì giá trị mới lớn hơn max bị
  `np.histogram` bỏ đi, và drift ra ngoài khoảng (đúng loại drift nguy hiểm nhất) trở nên vô hình.
- **Biên trùng.** Biến như `n_items` có khoảng 90% bằng 1: nhiều quantile bằng nhau. `np.unique`
  gộp chúng, nên số bin thật có thể ít hơn `bins`.
- **Bin rỗng.** $$\ln(a/e)$$ không xác định khi một trong hai bằng 0. Chặn dưới bằng một `eps` nhỏ
  là quy ước phổ biến; nó làm PSI phụ thuộc vào `eps` khi có bin rỗng (bin mới chiếm 10% với
  `eps = 1e-4` đóng góp khoảng 0.69). Vì thế ngưỡng cảnh báo phải đi kèm cách tính cụ thể.

**PSI phân loại** giống hệt, chỉ thay bin bằng giá trị. NaN là một giá trị riêng: tỉ lệ thiếu dữ
liệu tăng đột ngột (một service upstream ngừng gửi trường đó) là một trong những drift hay gặp
nhất trên production.

**KS.** Đánh giá hai ECDF tại mọi điểm của mẫu gộp. `side="right"` cho đúng định nghĩa
$$F(x) = P(X \le x)$$; dùng `side="left"` thì sai khi có giá trị trùng (test với số nguyên bắt lỗi
này).

## Olist: `delay_days` giữa train và test

| Thước đo | Giá trị |
| --- | --- |
| PSI train → test | 0.073 (`stable`) |
| KS statistic | 0.0785 |
| KS p-value (scipy) | khoảng 5e-99 |

Hai cách đọc trái ngược: KS nói "khác biệt cực kỳ có ý nghĩa", PSI nói "ổn định". Cả hai đều
đúng: với khoảng 43 nghìn và 32 nghìn đơn, kiểm định phát hiện được cả khác biệt rất nhỏ. Câu hỏi
cho monitoring không phải "có khác không" (dữ liệu thật luôn khác) mà "khác **đủ lớn** để đáng
đánh thức ai đó không". Vì vậy:

- Cảnh báo theo độ lớn (PSI, hoặc chính thống kê KS so với một ngưỡng như 0.1), không theo p-value.
- Ngưỡng 0.1 / 0.25 là quy ước từ ngành credit scoring, không phải định luật. Hiệu chỉnh lại bằng
  dữ liệu của bạn: PSI giữa các tháng "bình thường" trong quá khứ dao động cỡ nào?

Nhìn theo tháng (bài Intermediate 03) thì khác: PSI `delay_days` tháng 6/2018 lên khoảng 0.65,
vì gần như không đơn nào trễ. Drift lớn nhưng theo hướng **tốt**, nên phản ứng đúng là điều tra
chứ không phải tự động retrain.

## Sai lầm hay gặp

- Tính biên bin trên mẫu hiện tại hoặc trên mẫu gộp: reference phải cố định, nếu không PSI của
  tuần này và tuần trước không so được với nhau.
- Quên bỏ NaN ở biến số: `np.quantile` trả NaN và mọi thứ sau đó vô nghĩa mà không báo lỗi.
- Dùng p-value của KS hay chi-square làm ngưỡng cảnh báo trên dữ liệu lớn: báo động mỗi ngày,
  team nhanh chóng tắt cảnh báo.
