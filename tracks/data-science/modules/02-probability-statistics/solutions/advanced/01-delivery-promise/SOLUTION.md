# Hướng làm: mô hình thời gian giao và chính sách ngày hẹn

## Con số nền trên Olist thật

96 470 đơn giao xong. Thời gian giao (mua → nhận): median 10.22 ngày, CI 95% [10.18, 10.26]; p90
23.10 [22.98, 23.20]; p95 29.27 [29.08, 29.66]. Ngày hẹn hiện tại: median 23.23 ngày sau khi mua,
tức median đơn đến sớm khoảng 12 ngày so với hẹn, 73.9% đơn đến sớm ít nhất 7 ngày. Vậy mà vẫn
8.1% đơn trễ. Review xấu: 54.1% ở đơn trễ, 9.2% ở đơn đúng hẹn.

Chẩn đoán: ngày hẹn hiện tại vừa **quá dài** cho phần lớn đơn vừa **quá ngắn** cho một nhóm đơn. Đó
là dấu hiệu ngày hẹn không phân biệt đủ theo tuyến (bang, khoảng cách, seller).

## Mô hình phân phối

| Phân phối | log-likelihood | AIC | q95 (ngày) |
| --- | --- | --- | --- |
| lognorm | −322 190 | 644 383 | 30.72 |
| gamma | −324 122 | 648 249 | 28.21 |
| weibull_min | −328 398 | 656 799 | 29.25 |
| expon | −340 575 | 681 153 | 37.62 |

Lognormal thắng AIC nhưng q95 của nó (30.72) nằm ngoài CI của q95 thực nghiệm [29.08, 29.66]; Weibull
khớp q95 tốt hơn dù AIC kém hơn nhiều; Exponential sai hẳn (q95 37.6). Bài học: **AIC trả lời "mô
hình nào khớp toàn bộ phân phối", không trả lời "mô hình nào đúng ở chỗ tôi cần"**. Với 96 nghìn đơn,
đặt ngày hẹn từ percentile thực nghiệm; mô hình phân phối có ích cho nhóm ít đơn (bang RR 41 đơn) hoặc
khi cần một phân phối dự báo theo đặc trưng của từng đơn (quantile regression, hoặc mô hình tham số với
tham số phụ thuộc đặc trưng).

## Chính sách thử nghiệm

| Chính sách | Median ngày hẹn | Tỉ lệ trễ |
| --- | --- | --- |
| Hiện tại | 23.23 | 8.1% |
| p95 theo bang (trong mẫu) | 24.66 | 5.0% |
| p90 theo bang (trong mẫu) | 20.20 | 10.0% |
| p90 theo bang, ước lượng trên 2017, đánh giá trên 01–08/2018 | 19.30 | 10.8% (ngày hẹn thật của giai đoạn này: 9.4%) |

Đọc bảng: chỉ cần hẹn theo percentile của từng bang, Olist có thể giữ ngày hẹn gần như cũ mà giảm tỉ lệ
trễ từ 8.1% xuống khoảng 5%, hoặc hẹn ngắn hơn khoảng 3 ngày với tỉ lệ trễ khoảng 10%. Đánh giá
ngoài thời gian (2017 → 2018) trễ nhiều hơn trong mẫu: phân phối thay đổi theo thời gian (mùa, lượng
đơn tăng), nên chính sách phải cập nhật định kỳ và theo dõi.

Chọn percentile nào là quyết định kinh doanh: cần ước lượng tác động của ngày hẹn lên conversion (dữ
liệu Olist không có, cần thí nghiệm, module 03) và tác động của trễ lên review / mua lại. Báo cáo tốt
nêu rõ đánh đổi và đề xuất thí nghiệm, không tự chọn một con số rồi khẳng định là tối ưu.

## Các quyết định thiết kế cần cân nhắc

- **Survivorship.** Chỉ đơn đã giao có thời gian giao; 2 963 đơn không ở trạng thái `delivered`
  (huỷ, đang giao, không giao được). Nếu đơn huỷ vì giao quá lâu, percentile thực đang bị đánh giá thấp.
- **Phân nhóm.** Bang là chiều đơn giản nhất; seller, khoảng cách seller–khách, category (hàng cồng
  kềnh) đều làm thay đổi phân phối. Nhóm ít đơn cần shrinkage (gộp về vùng, hoặc mô hình).
- **CI của percentile.** p95 của RR ước lượng trên 41 đơn có CI cực rộng; đừng đặt chính sách theo nó.
- **Ngày hẹn ảnh hưởng ngược lại hành vi.** Seller có thể "thong thả" hơn khi ngày hẹn xa hơn; chính
  sách mới làm thay đổi chính phân phối đã dùng để đặt nó.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hiện trạng có số liệu | 15 | Median, p90, p95 kèm CI; so với ngày hẹn hiện tại; tỉ lệ trễ và review xấu theo trễ |
| Mô hình phân phối | 20 | So nhiều họ bằng AIC **và** kiểm tra đuôi; giải thích vì sao mô hình thắng AIC vẫn có thể không dùng |
| Chính sách | 25 | Ít nhất hai phương án có định lượng (ngày hẹn, tỉ lệ trễ); phân nhóm có lý do; xử lý nhóm ít đơn |
| Kiểm tra ngoài mẫu | 15 | Ước lượng trên quá khứ, đánh giá trên giai đoạn sau; nhận xét về độ ổn định |
| Đánh đổi kinh doanh | 15 | Nêu rõ conversion vs trễ / review; đề xuất thí nghiệm để đo phần chưa biết |
| Giới hạn | 10 | Survivorship, mùa vụ, phản ứng của seller với chính sách |

Từ 70 điểm trở lên: đủ để trình bày với Trưởng Vận hành.
