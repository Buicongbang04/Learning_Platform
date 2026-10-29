# Lời giải: đổi metric model ra tiền

## Cách làm

Với k đơn được chọn và precision π, tổng giá trị là

$$
\mathrm{EV} = TP\,(\Delta V - C) - FP\,C = k\,(\pi\,\Delta V - C),
$$

nên hành động có lãi khi và chỉ khi $$\pi > \pi^* = C / (\Delta V)$$. `break_even_precision` trả
đúng công thức, không cắt ở 1: con số 1.11 nói với người đọc nhiều hơn "không có lãi" (hành động cần
rẻ hơn 10% hoặc hiệu quả hơn 11% mới hoà vốn ngay cả với model hoàn hảo).

`best_threshold_value` sắp p giảm dần, `cumsum` cho TP của top i đơn, rồi chỉ giữ vị trí **cuối** của
mỗi nhóm p bằng nhau, vì ngưỡng t chọn mọi đơn có `p >= t`, không chọn được nửa nhóm. Nếu không ngưỡng
nào cho giá trị dương thì trả `np.inf`: không hành động, giá trị 0.

## Đọc kết quả

| Kênh | C | π* với V = 30 R$, Δ = 0.15 |
| --- | --- | --- |
| Gọi điện CSKH | 5 R$ | 111.1%: không bao giờ có lãi |
| Tin nhắn tự động | 0.5 R$ | 11.1% |

Trên Olist, tỉ lệ trễ của tập test là 6.0%: nhắn cho mọi đơn là lỗ. Model lúc giao vận chuyển có
precision 39.1% ở top 5% (lý thuyết, mục 3), xa trên 11.1%. Nhưng nếu Δ thật chỉ là 0.05 thì π* thành
33.3% và chính sách top 10% (precision 26.4%) bắt đầu lỗ. Hai con số V và Δ đáng kiểm chứng hơn mọi
lần tuning model.

## Bẫy thường gặp

- Coi FN là chi phí đầy đủ V (như module 11) khi hành động chỉ cứu được một phần: phóng đại giá trị
  1/Δ lần.
- Quên chi phí hành động trên TP (liên hệ đúng đơn vẫn tốn tiền).
- Chọn ngưỡng tối ưu trên chính tập dùng để báo cáo giá trị: con số bị lạc quan. Chọn trên validation,
  báo cáo trên test.
- Dùng công thức ngưỡng $$t^* = \pi^*$$ trên xác suất chưa calibrate.
