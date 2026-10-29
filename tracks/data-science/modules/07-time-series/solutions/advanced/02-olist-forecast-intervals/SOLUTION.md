# Hướng làm: khoảng dự báo số đơn Olist

Bài Advanced không có đáp án duy nhất. Dưới đây là hướng làm, các số tham chiếu chạy trên dữ liệu
thật khi soạn bài, và rubric.

## 1. Thiết lập

- Chuỗi: số đơn mỗi ngày 2017-01-09 tới 2018-08-19 (như Intermediate 02).
- Hiệu chỉnh: 38 origin mỗi 7 ngày từ 2017-06-04 tới 2018-02-18, sai số 14 bước.
- Đánh giá: 12 origin mỗi 14 ngày từ 2018-03-04 (168 ngày được dự báo).
- Mức danh nghĩa 80% (α = 0.2). Tách hiệu chỉnh và đánh giá là bắt buộc: dùng cùng các origin để
  dựng và chấm khoảng sẽ cho coverage đẹp giả.

## 2. Kết quả tham chiếu

| Model điểm | Cách dựng khoảng | Coverage (danh nghĩa 80%) | Interval score | Độ rộng TB (đơn) |
| --- | --- | --- | --- | --- |
| Seasonal naive | empirical additive | 68.5% | 214.5 | 107.6 |
| Seasonal naive | empirical log-ratio | 78.0% | 223.2 | 151.8 |
| SARIMA(1,1,1)(0,1,1)[7] | empirical additive | 66.7% | 179.4 | 100.7 |
| SARIMA(1,1,1)(0,1,1)[7] | empirical log-ratio | 83.3% | 175.0 | 138.3 |
| SARIMA(1,1,1)(0,1,1)[7] | lý thuyết (`conf_int`) | 94.0% | 191.2 | 171.2 |

Interval score thấp hơn là tốt hơn; nó thưởng khoảng hẹp và phạt nặng (hệ số 2/α = 10) mỗi điểm
nằm ngoài.

## 3. Đọc kết quả

1. **Empirical additive phủ thiếu** (67–69%): giai đoạn hiệu chỉnh (giữa 2017 tới đầu 2018) có mức
   thấp hơn 2018, nên sai số **tuyệt đối** nhỏ hơn. Chuỗi tăng trưởng cần sai số tương đối.
2. **Log-ratio sửa được phần lớn**: coverage 78–83%, gần danh nghĩa, vì độ rộng tỉ lệ theo mức.
3. **Khoảng lý thuyết của SARIMA phủ thừa** (94% cho khoảng 80%) và rộng nhất: giả định sai số
   chuẩn, phương sai không đổi, và Black Friday trong dữ liệu train làm phương sai ước lượng phình
   ra. Phủ thừa không "an toàn": kho thuê thừa người mỗi ngày.
4. Tốt nhất theo interval score: SARIMA + log-ratio (175.0). Đây là khuyến nghị hợp lý, kèm cảnh
   báo chỉ dựa trên 12 origin.
5. **Chọn phân vị theo chi phí**: thiếu một nhân viên tốn gấp 4 lần thừa, phân vị tối ưu là
   4 / (4 + 1) = 0.8. Lập kế hoạch theo cận trên của khoảng 60% trung tâm (phân vị 0.8), không theo
   dự báo điểm và không theo cận trên khoảng 80% (phân vị 0.9). Pinball loss ở q = 0.8 là đúng chi phí
   kỳ vọng tỉ lệ với bài toán này, nên dùng nó để chọn cách dựng khoảng.
6. **Sự kiện**: Black Friday 2017 (1 176 đơn, seasonal naive dự báo 197) và tuần 21–27/5/2018 (số
   đơn giảm một nửa) nằm ngoài mọi khoảng. Khoảng dự báo thống kê chỉ phủ "những ngày giống quá khứ";
   sự kiện biết trước phải được đưa vào bằng biến ngoại sinh hoặc điều chỉnh thủ công có ghi lại.

## 4. Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Code và test | 15 | Mọi test pass |
| Thiết kế đánh giá | 20 | Tách origin hiệu chỉnh và đánh giá; coverage tính trên dữ liệu chưa dùng |
| So sánh cách dựng khoảng | 20 | Ít nhất 3 cách × 2 model, cả coverage lẫn interval score |
| Giải thích | 20 | Vì sao additive phủ thiếu, vì sao khoảng lý thuyết phủ thừa |
| Quyết định theo chi phí | 15 | Chọn phân vị theo tỉ lệ chi phí, dùng pinball loss hoặc lập luận newsvendor |
| Báo cáo | 10 | Ngôn ngữ vận hành ("bình thường X đơn, ngày bận Y đơn"), có quy trình cho sự kiện |

Từ 70 điểm: mức DS mid-level. Từ 85: senior.

## 5. Mở rộng

- Conformal prediction theo horizon (split conformal là chính cách empirical ở đây; adaptive
  conformal cập nhật mức phân vị khi coverage gần đây lệch).
- Dự báo phân vị trực tiếp: LightGBM với `objective="quantile"` cho từng q.
- Khoảng cho tổng 14 ngày (kế hoạch tuần) khác với khoảng cho từng ngày: sai số các ngày tương quan.
