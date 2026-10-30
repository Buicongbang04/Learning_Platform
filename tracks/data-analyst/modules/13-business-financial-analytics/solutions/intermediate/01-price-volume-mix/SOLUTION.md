# Lời giải: price-volume-mix bridge mùa cao điểm

## Cách làm

- **`product_sales`**: ép `Invoice` và `StockCode` sang `str` (Excel trộn kiểu), lọc dòng hợp lệ, mã bắt đầu bằng
  chữ số (`str.match(r"\d")`), kỳ nửa mở `[start, end)` để ngày 30/11 23:59 thuộc kỳ còn 01/12 00:00 thì không.
  `price = revenue / units` là **giá bình quân thực thu**, không phải giá niêm yết: nó đổi cả khi giá niêm yết đứng
  yên nhưng khách mua ở mức giá sỉ khác hoặc hàng bị bán xả.
- **`pvm_bridge`**: trên sản phẩm chung, công thức trong notebook là một lựa chọn quen dùng (giá trên lượng kỳ mới,
  lượng và mix theo giá kỳ gốc). Ba hiệu ứng cộng đúng thay đổi doanh thu của sản phẩm chung vì

$$
\sum p_1 q_1 - \sum p_0 q_0 = \sum (p_1 - p_0) q_1 + \sum p_0 (q_1 - q_0), \qquad \sum p_0 (q_1 - q_0) = \text{volume} + \text{mix}
$$

  `new` và `lost` đứng riêng vì mã mới không có giá kỳ gốc (và mã ngừng không có giá kỳ mới).
- **`product_effects`**: hai cột chính là hai số hạng của đẳng thức trên cho từng mã; dùng để tìm mã nào kéo hiệu
  ứng giá hoặc lượng.

## Kết quả trên bộ thật

| Chỉ tiêu | 09-11/2010 | 09-11/2011 |
| --- | --- | --- |
| Doanh thu gộp (mọi dòng hợp lệ) | 3 560 089 | 3 723 066 |
| Trong đó không phải hàng hoá | 154 758 | 128 188 |
| Doanh thu hàng hoá | 3 405 332 | 3 594 878 (+5.6%) |
| Số mã | 3 323 | 3 224 (2 481 chung, 743 mới, 842 ngừng) |
| Số lượng của mã chung | 1 767 153 | 1 378 419 (−22.0%) |

| Hiệu ứng | GBP |
| --- | --- |
| price | −117 399 |
| volume | −690 654 |
| mix | +82 547 |
| new | +1 180 727 (32.8% doanh thu hàng hoá 2011) |
| lost | −265 676 (7.8% doanh thu hàng hoá 2010) |
| **Tổng** | **+189 546** |

Đọc: **toàn bộ tăng trưởng đến từ mã mới**. Doanh thu của 2 481 mã cũ giảm từ 3.14 xuống 2.41 triệu (−23%), chủ yếu
vì bán ít đi. Mã mới lớn nhất: 23084 RABBIT NIGHT LIGHT 47 513 GBP, 23355 HOT WATER BOTTLE KEEP CALM 24 274, 23284
DOORMAT KEEP CALM AND COME IN 21 596.

Hiệu ứng giá âm tập trung ở đồ Giáng sinh tồn kho: 22065 CHRISTMAS PUDDING TRINKET POT giá thực thu 1.45 → 0.46,
median giá dòng 1.45 → 0.39 trong khi giá cao nhất gần như giữ (3.36 → 3.29); 22577/22578 (sao, tim gỗ Giáng sinh)
median 0.85 → 0.29. Đây là **bán xả** (và bán theo lô lớn hơn: median số lượng mỗi dòng tăng khoảng gấp đôi hoặc hơn), không
phải giảm giá niêm yết. 48% mã chung có hiệu ứng giá âm, 47% dương; tổng phần âm −242 232, phần dương +124 834.

Câu cho Giám đốc kinh doanh: "Doanh thu hàng hoá mùa cao điểm tăng 190 nghìn GBP (+5.6%) nhờ 743 mã mới mang về
1.18 triệu; các mã cũ bán ít hơn 22% về số lượng (−691 nghìn) và bán xả đồ Giáng sinh tồn kho làm giá bình quân
giảm (−117 nghìn)."

## Đáp án trắc nghiệm

- `biggest-driver` **c**: mã mới +1.18 triệu. Hiệu ứng giá và lượng đều âm.
- `common-units` **a**: 1 767 153 → 1 378 419, −22%. Tổng số lượng mọi mã hàng hoá (kể cả mã mới) chỉ +0.4% (1 933 956 → 1 941 754), dễ nhầm với "gần như không đổi".
- `new-share` **b**: 1 180 727 / 3 594 878 = 32.8%. 8% là tỉ trọng mã ngừng trong kỳ gốc.
- `price-driver` **d**: max giá gần như giữ, median giảm mạnh, số lượng mỗi dòng tăng: bán xả. Đổi đơn vị (c) sẽ
  làm cả max giảm.
- `formula-order` **b**: với thứ tự ngược (giá trên lượng kỳ gốc, lượng và mix theo giá kỳ mới) giá +146 874, lượng
  −680 825, mix −191 555. Dấu của giá và mix đổi chỉ vì chọn công thức, nên báo cáo PVM phải ghi công thức và giữ cố
  định qua các kỳ; khi hai cách cho kết luận khác dấu, đừng đưa "hiệu ứng giá" làm thông điệp chính.
- `raise-prices` **c**: bridge mô tả chuyện đã xảy ra, không đo khách phản ứng thế nào nếu giá đổi (elasticity).
  Hiệu ứng giá âm ở đây là bán xả có chủ đích. Muốn biết tăng giá có lợi không cần thử nghiệm giá hoặc ít nhất so
  sánh có đối chứng (module 11), cộng với phép tính hoà vốn ở bài Basic 02.
- `mix-units` **a**: "một đơn vị" của mỗi mã khác nhau (gói 12 cái, một cái, một bộ), nên Q và tỉ trọng số lượng là
  cộng táo với cam. Khắc phục: làm PVM theo nhóm sản phẩm, hoặc thay số lượng bằng một đơn vị chung.
- `new-lost` **b**: không có giá kỳ gốc thì "đổi giá" vô nghĩa; ép giá gốc bằng 0 biến cả doanh thu mã mới thành
  "hiệu ứng giá" và che đi câu chuyện danh mục.

## Lỗi hay gặp

- Để mã phí (`POST`, `DOT`, `M`, `AMAZONFEE`) trong PVM: `M` (manual) có giá dòng từ vài xu tới hàng nghìn GBP,
  làm hiệu ứng giá vô nghĩa.
- Lấy tỉ trọng trên toàn bộ mã của từng kỳ: ba hiệu ứng không còn cộng đúng tổng của sản phẩm chung.
- So tháng 12 (chưa đủ ngày ở 2011) hoặc quên bỏ phần trùng 01-09/12/2010 khi ghép hai sheet.
