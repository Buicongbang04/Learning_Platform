# Lời giải: phân phối giá trị hoá đơn Online Retail II

## Cách làm

1. **`invoice_totals`**: đổi cả cột `Invoice` sang `str` (Excel đọc `489434` thành `int` nhưng
   `C489449` và `A506401` thành `str`), tạo mặt nạ trên từng **dòng** (không phải `C`, `Quantity > 0`,
   `Price > 0`), rồi cộng `Quantity * Price` theo mã. Lọc theo dòng chứ không loại cả hoá đơn: một hoá
   đơn có một dòng điều chỉnh vẫn là một đơn bán thật.
2. **`summary_stats`**: `mean`, `median`, `quantile(0.9)`, `quantile(0.99)`, `skew` của pandas, ép
   về `float` để kết quả không mang kiểu numpy ra báo cáo/JSON.
3. **`log_bins`**: kiểm `min > 0`, `np.logspace(log10(min), log10(max), n + 1)`, rồi gán lại biên
   đầu và cuối đúng bằng `min`, `max` để `np.histogram` không bỏ sót điểm do làm tròn.
4. Boxplot vẽ trên `log10` của giá trị: tứ phân vị và râu 1.5 IQR tính trên thang tuyến tính rồi
   hiển thị lên trục log sẽ cho râu trái kéo tới tận min và râu phải cụt, một hình méo do cách vẽ.

## Vì sao như vậy

- **Mean không phải "điển hình"** khi phân phối lệch phải: mean 491.90 GBP gần đúng bằng p75
  (491.75), tức chỉ 25% hoá đơn lớn hơn mean. Median 300.84 GBP mới là hoá đơn ở giữa. Báo median kèm
  khoảng p25–p75 (147.93–491.75) và ghi chú mean bị kéo bởi đơn sỉ.
- **Đuôi nhỏ về số lượng nhưng lớn về tiền**: 1% hoá đơn lớn nhất (211 hoá đơn, từ 4 099 GBP trở lên)
  mang 16.8% doanh thu. Một chart chỉ thấy "khối điển hình" sẽ giấu nhóm khách quan trọng nhất về
  doanh thu; một chart chỉ thấy đuôi thì giấu khách lẻ.
- **Chọn chart**: histogram tuyến tính vô dụng (bin rộng khoảng 1 000 GBP, 91% hoá đơn nằm dưới
  1 000 GBP). Histogram bin log trên trục log cho thấy cả hai phần: khối chính gần đối xứng quanh
  median trên thang log (đuôi trái là các hoá đơn vài GBP), dáng gần log-normal. ECDF trả lời
  trực tiếp câu "bao nhiêu % hoá đơn dưới X GBP" (91.2% dưới 1 000 GBP) và không phụ thuộc cách chọn
  bin. Cho slide của Head of Sales: histogram bin log
  có đường median, headline kiểu "Hoá đơn điển hình 301 GBP; 1% đơn sỉ trên 4 100 GBP mang 17% doanh
  thu". ECDF hợp hơn cho người đọc quen phân vị (team pricing, finance).
- **Bước 3 của quy trình đọc chart (điểm bất thường)**: ECDF dốc đứng ngay trên 300 GBP. Phóng to
  thấy bin 290–300 có 338 hoá đơn còn bin 300–310 có 739. Phân phối tự nhiên không có bậc như vậy;
  khả năng là một **ngưỡng kinh doanh** (giá trị tối thiểu để được ưu đãi, miễn phí giao hàng hoặc
  giá sỉ), khiến khách gom thêm hàng cho vượt 300 GBP. Đây là **quan sát**; kết luận cần xác nhận với
  team kinh doanh về chính sách giá/giao hàng thời điểm đó. Nếu đúng, đó là bằng chứng ngưỡng ưu đãi
  có tác dụng lên hành vi đặt hàng, câu hỏi đáng phân tích tiếp.

## Con số tham chiếu (bộ thật, sheet `Year 2009-2010`)

| Đại lượng | Giá trị |
| --- | --- |
| Dòng / mã hoá đơn / mã huỷ | 525 461 / 28 816 / 4 592 |
| Hoá đơn hợp lệ, tổng doanh thu | 20 951, 10 305 892 GBP |
| mean, median | 491.90, 300.84 |
| p25, p75, p90, p99 | 147.93, 491.75, 920.70, 4 098.96 |
| min, max, skew | 0.19, 49 844.99, 17.64 |
| Hoá đơn lớn hơn mean | 25.0% |
| 1% hoá đơn lớn nhất | 211 hoá đơn, 16.8% doanh thu |
| ECDF tại 1 000 GBP | 91.2% |

## Đáp án trắc nghiệm

- `mean-vs-median` (b) **mean 492, median 301**. Phương án (c) 534/304 là số của sheet 2010-2011 trong
  lý thuyết module: luôn kiểm bước 1 "kỳ nào, lọc gì" trước khi chép số.
- `share-above-mean` (b) **khoảng 25%**: mean nằm ở p75.
- `top1-revenue` (c) **khoảng 17%** (16.8%).
- `ecdf-cliff` (c) **300 GBP**: 338 → 739 hoá đơn giữa hai bin 10 GBP liền nhau.
- `linear-hist` (a): 50 bin đều trên 0.19–49 845 GBP, mỗi bin rộng khoảng 1 000 GBP. (b) sai vì
  `invoice_totals` đã bỏ hoá đơn huỷ và mọi giá trị đều dương; (c) thêm bin vẫn để đuôi chiếm gần hết
  trục x; (d) matplotlib không gộp bin.
- `tail-chart` (b): trục log trải đều các bậc độ lớn nên thấy cả khối 100–1 000 GBP lẫn đuôi trên
  10 000 GBP. Cắt bỏ trên p99 (c) giấu đúng phần mang 17% doanh thu; bar trung bình theo tháng (a)
  trả lời câu hỏi xu hướng và vẫn dùng mean; pie (d) là câu hỏi thành phần, không cho thấy phân phối.
- `typical-value` (c): median kèm p25–p75. Mean (a) bị đơn sỉ kéo; trimmed mean (b) tốt hơn mean nhưng
  ngưỡng cắt tuỳ ý và khó giải thích; max (d) là một điểm cực trị.
