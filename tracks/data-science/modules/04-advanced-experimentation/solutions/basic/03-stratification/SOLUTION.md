# Lời giải: stratified sampling và post-stratification

## Cách làm

- `strata_from_quantiles`: `pd.qcut(x, q, labels=False)`. Quantile bảo đảm các tầng cỡ bằng nhau,
  tránh tầng quá nhỏ làm variance trong tầng ước lượng kém.
- `stratified_assign`: trong mỗi tầng, hoán vị ngẫu nhiên các chỉ số rồi gán xen kẽ. Bốc ngẫu nhiên
  `first_arm` để nhánh nhận đơn vị thừa không cố định; nếu không, 50 tầng 3 đơn vị cho ra 100
  control và 50 treatment.
- `post_stratified_effect`: một `groupby` + `unstack` cho bảng tầng × nhánh, rồi áp đúng công thức.
  Trọng số $$w_k$$ là tỉ lệ **của tầng trong tổng thể** (cả hai nhánh), không phải tỉ lệ trong từng
  nhánh: đó là điều làm ước lượng không lệch kể cả khi random đơn giản tình cờ gửi nhiều cửa hàng
  lớn vào một nhánh.

## Vì sao hiệu quả

Variance của hiệu trung bình thông thường gồm hai phần: biến thiên **trong** tầng và biến thiên
**giữa** các tầng. Chia tầng loại bỏ phần giữa tầng. Trong test, mức metric của 4 tầng là 10, 30,
60, 120 với nhiễu trong tầng chỉ 8, nên phần giữa tầng chiếm gần hết: độ lệch chuẩn của ước lượng
còn khoảng 0.23 lần.

Trên Rossmann thật (doanh số trung bình ngày của 1 115 cửa hàng, tháng 6/2015), chia tầng theo
`StoreType` chỉ giảm 4.0% variance, vì loại cửa hàng giải thích rất ít khác biệt doanh số. Chia
theo 10 decile doanh số tháng trước giảm 85.9%, còn CUPED với chính doanh số tháng trước giảm
98.2%. Bài học: tầng tốt là tầng **dự đoán được metric**, không phải tầng "nghe có vẻ hợp lý".

## Stratified sampling hay post-stratification

| | Stratified sampling (chia tầng lúc gán) | Post-stratification (chia tầng lúc phân tích) |
| --- | --- | --- |
| Cần biết tầng khi nào | Trước khi random, cho mọi đơn vị | Chỉ cần lúc phân tích |
| Hạ tầng | Phải sửa hệ thống assignment, khó với user đến theo thời gian thực | Chỉ là phép tính |
| Lợi thêm | Cân bằng chính xác; lợi rõ khi **ít đơn vị** (vài chục cửa hàng, thành phố) | Gần như bằng stratified sampling khi n lớn |
| Đổi tầng | Phải chạy lại | Thử được nhiều cách, nhưng phải định trước để tránh "chọn tầng cho p đẹp" |

Bài báo của Netflix (Xie và Aurisset, KDD 2016, mục 6) so sánh hai cách trên dữ liệu thật và đi tới kết
luận cùng hướng: với lượng user lớn, điều chỉnh sau khi gán (post-stratification, CUPED) cho lợi
ích tương đương mà đơn giản hơn nhiều. Stratified sampling đáng công khi số đơn vị nhỏ, như thí
nghiệm theo cửa hàng ở bài Advanced 01.

## Bẫy thường gặp

- Chia quá nhiều tầng nhỏ: mỗi tầng vài đơn vị thì variance trong tầng ước lượng rất nhiễu, có tầng
  thiếu hẳn một nhánh. Quy tắc thực tế: mỗi ô tầng × nhánh có ít nhất vài chục đơn vị.
- Dùng biến **sau** can thiệp để chia tầng (ví dụ "user có dùng tính năng mới không"): tầng bị
  treatment làm thay đổi, ước lượng bị lệch.
- Quên rằng stratified sampling cũng phải phân tích theo tầng: dùng t-test thông thường trên dữ
  liệu đã gán theo tầng cho SE **quá lớn** (bảo thủ), mất phần lợi đã trả công.
