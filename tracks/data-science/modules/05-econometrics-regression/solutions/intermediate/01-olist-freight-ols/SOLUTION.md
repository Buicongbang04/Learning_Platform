# Lời giải: phí ship Olist

Notebook lời giải: `freight.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Dựng bảng

- Đơn **một món** được xác định từ `items` trước mọi phép nối. Lọc sau khi nối với products hoặc
  geolocation sẽ đếm sai khi có dòng bị mất.
- Toạ độ mỗi zip prefix dùng **trung vị**: bảng geolocation có toạ độ lỗi (42 dòng nằm ngoài khung toạ độ của Brazil),
  trung vị ít bị kéo hơn trung bình.
- Bỏ khoảng cách 0 (cùng prefix): không đo được khoảng cách thật, và `log` không xác định.
- Kết quả: 86 065 đơn, 2 879 seller.

## Kết quả

| Hệ số | Giá trị | SE cổ điển | SE HC3 | SE cluster (seller) |
| --- | --- | --- | --- | --- |
| `log_weight` | 0.1345 | 0.0013 | 0.0015 | 0.0109 |
| `log_volume` | 0.0298 | 0.0012 | 0.0013 | 0.0089 |
| `log_distance` | 0.1418 | 0.0011 | 0.0011 | 0.0038 |
| `same_state` | −0.2242 | 0.0031 | 0.0028 | 0.0108 |
| `log_price` | 0.0964 | 0.0013 | 0.0014 | 0.0064 |

$$R^2 = 0.655$$. Diễn giải: khoảng cách gấp đôi +10.3%; cùng bang −20.1%; nặng hơn 10% +1.3%.

## Chẩn đoán

- **Residual vs fitted**: chia fitted thành 10 decile, residual trung bình là +0.07 ở decile thấp
  nhất, −0.08 ở decile 7–8, +0.16 ở decile cao nhất: hình chữ U nhẹ, dạng hàm log-log chưa đủ (bảng
  cước theo bậc cân nặng, phụ phí hàng cồng kềnh). Thử spline cho `log_weight` là bước tiếp hợp lý.
  Độ lệch chuẩn residual tăng từ 0.19 (decile thấp) lên 0.49 (decile cao): heteroskedasticity
  (Breusch-Pagan LM = 8 494), nhưng tỉ lệ HC3 / cổ điển chỉ 0.91–1.17 nên ảnh hưởng tới SE nhỏ.
- **QQ-plot**: đuôi phải nặng (skewness residual 1.30). Với 86 nghìn dòng, không ảnh hưởng inference
  cho hệ số; ảnh hưởng nếu dùng model để dựng khoảng dự đoán cho từng đơn.
- **Theo seller**: residual trung bình của các seller có từ 30 đơn lệch chuẩn 0.149 (tức seller "đắt"
  hay "rẻ" hơn kỳ vọng khoảng ±15%). Đây là lý do cluster SE lớn gấp 3.5–8.7 lần: thông tin độc lập
  gần với số seller hơn là số đơn. Biến thay đổi chủ yếu **giữa** seller (cân nặng, giá: mỗi seller
  bán một loại hàng) bị ảnh hưởng nhiều nhất; khoảng cách thay đổi trong từng seller (khách ở nhiều
  nơi) nên ít bị hơn.
- **Omitted variable bias**: bỏ `same_state`, hệ số `log_distance` từ 0.1418 lên 0.2001. Khoảng cách
  và cùng bang tương quan −0.74; model thiếu biến gán phần "khác bang" cho khoảng cách.

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| Độ lớn bằng ngôn ngữ kinh doanh | Nói "gấp đôi khoảng cách thì +10%", không nói "hệ số 0.14" |
| SE | Báo cáo cluster SE theo seller và giải thích vì sao |
| Giới hạn | Nhận ra `log_price` là proxy, không phải cơ chế; không nói nhân quả |
| Bước tiếp | Đề xuất cụ thể: hiệu ứng tuyến, seller FE, phân tích residual theo seller có shrinkage |

## Sai lầm hay gặp

- So $$R^2$$ của model log với model tuyến tính trên `freight_value` (0.588) để chọn model: hai y
  khác nhau, không so được.
- Báo cáo SE cổ điển với 86 nghìn dòng và kết luận "mọi thứ cực kỳ chắc chắn".
- Dùng `np.exp(dự đoán log)` làm phí ship trung bình dự kiến: đó là median; cần smearing nếu cần mean.
- Đọc zip prefix dạng số: `01037` thành `1037`, nối toạ độ sai hoặc mất dòng.
