# Lời giải: metric tree doanh thu và phân rã thay đổi

## Cách làm

1. **`_clean`**: đổi `Invoice` sang `str` trước khi kiểm tiền tố `C` (Excel đọc `536365` thành số, `C536379` thành
   chữ), lọc theo **dòng** (`Quantity > 0`, `Price > 0`), thêm `revenue`.
2. **`monthly_tree`**: tháng = `InvoiceDate.dt.to_period("M").dt.to_timestamp()`. Doanh thu gộp nhóm trên mọi dòng
   hợp lệ; `known_revenue`, `customers` (`nunique` của `Customer ID`), `orders` (`nunique` của `Invoice`) nhóm trên
   các dòng có `Customer ID`, rồi `join` theo tháng và `fillna(0)`. `frequency = orders / customers`,
   `aov = known_revenue / orders`, nên tích ba thành phần bằng `known_revenue` tuyệt đối (sai số làm tròn 1e-10).
   Đếm `orders` chỉ trên dòng có mã là bắt buộc: đếm cả hoá đơn không mã thì AOV không còn khớp với nhánh khách.
3. **`decompose`**: trọng số `L = (R1 - R0) / (ln R1 - ln R0)` (trung bình log của hai mức doanh thu), đóng góp
   `L * ln(X1 / X0)` cho từng thành phần, `guest` là chênh lệch tuyệt đối. Khi `R1 = R0` dùng `L = R0`.

## Vì sao như vậy

- **Cây có nhánh không mã**: 16.5% doanh thu gộp cả năm không có `Customer ID`. Bỏ nhánh này (như nhiều báo cáo
  "doanh thu theo khách" vẫn làm) thì mức tăng tháng 11 bị hiểu sai hoàn toàn (xem dưới).
- **LMDI thay vì thay lần lượt**: thay lần lượt cũng cộng đúng tổng, nhưng phần tương tác bị gán cho thành phần
  thay sau. Tháng 10 → 11/2011: thay khách → tần suất → AOV cho AOV −269 738 GBP, tần suất +163 647; thay AOV →
  tần suất → khách cho AOV −195 832, tần suất +108 868. LMDI cho −229 535 và +133 463, nằm giữa, và không phụ thuộc
  thứ tự nên hai DA luôn báo cùng số.
- **Kiểm tổng**: luôn in tổng các đóng góp cạnh mức thay đổi thật. Lệch là dấu hiệu lỗi định nghĩa (đếm đơn trên
  tập khác với doanh thu).

## Đọc ba cặp tháng

| Cặp tháng | Δ doanh thu gộp | Khách | Tần suất | AOV | Không mã |
| --- | --- | --- | --- | --- | --- |
| 12/2010 → 1/2011 | −132 382 (−16.1%) | −101 416 | −98 209 | +196 356 | −129 113 |
| 10 → 11/2011 | +354 517 (+30.7%) | +218 570 | +133 463 | −229 535 | +232 018 |
| 11 → 12/2011 | −870 686 (−57.7%) | −793 475 | −185 638 | +335 505 | −227 079 |

- **Tháng 10 → 11/2011**: "Doanh thu tăng 355 nghìn GBP (+31%), nhưng **65%** mức tăng (232 nghìn) đến từ đơn
  không có mã khách, trong đó hai hoá đơn 52 941 và 50 654 GBP ngày 7 và 14/11. Phần khách có mã tăng 11.8%: thêm
  22% khách và mua thường hơn 13%, nhưng đơn nhỏ hơn 19%." Câu hỏi tiếp theo: hai hoá đơn lớn không mã là ai (đơn
  sỉ nhập tay? cùng một khách?), và AOV giảm có phải vì nhiều khách nhỏ mùa Giáng sinh. Đừng quy mức tăng cho
  chiến dịch marketing trước khi trả lời được câu đó.
- **Tháng 12/2010 → 1/2011**: doanh thu khách có mã gần như phẳng (−0.6%) nhưng **bên dưới không phẳng**: khách
  −16.3%, tần suất −15.8%, AOV +41.0% bù lại. AOV tháng 1 bị đẩy bởi hoá đơn 541431 (77 183.60 GBP, 74 215 hũ gốm
  của khách 12346) **bị huỷ ngay** bằng C541433. Doanh thu gộp theo định nghĩa chung vẫn tính nó (quy tắc lọc theo
  dòng không ghép hoá đơn huỷ với hoá đơn gốc); bỏ nó thì AOV tháng 1 còn 499 GBP (+22% so với 409 GBP). Bài học:
  một con số tổng phẳng có thể che các thành phần chuyển động mạnh ngược chiều, và một thành phần nhảy vọt thì
  kiểm outlier trước khi kể chuyện.
- **Tháng 11 → 12/2011**: không đưa cho CEO. Tháng 12 chỉ có dữ liệu tới ngày 9 (8 ngày giao dịch); số khách
  −63% là do tháng chưa hết. So 9 ngày đầu tháng với cùng kỳ (module 08) thay vì cả tháng. Nhân với 31/9 (d trong
  quiz) cũng sai vì doanh thu trong tháng 12 dồn vào đầu tháng (đặt hàng Giáng sinh).

## Con số tham chiếu

| Đại lượng | Giá trị |
| --- | --- |
| Tháng, doanh thu gộp | 13 tháng, 10 666 702.54 GBP |
| Tỉ trọng có `Customer ID` | 83.5% |
| Tháng 11/2011 | 1 664 khách, 2 657 đơn, tần suất 1.60, AOV 437.27, không mã 347 679 GBP |
| Tháng 10/2011 | 1 364 khách, 1 929 đơn, tần suất 1.41, AOV 538.79, không mã 115 661 GBP |
| Dòng thiếu `Customer ID` (dữ liệu thô) | 24.9% |

## Đáp án trắc nghiệm

- `known-share` (c) **khoảng 84%** (83.5%). 75% (b) là tỉ lệ **dòng** có mã (24.9% dòng thiếu mã): dòng không mã
  thường là đơn lẻ giá trị nhỏ, nên tỉ trọng doanh thu cao hơn tỉ trọng dòng.
- `nov-guest-share` (c) **khoảng 65%**: 232 018 / 354 517.
- `nov-negative-branch` (a) **AOV**: −229 535 GBP (AOV −18.8%).
- `dec-jan-flat` (b): khách −16.3%, tần suất −15.8%, AOV +41.0%.
- `jan-big-invoice` (b): huỷ ngay bằng C541433 cùng số lượng. Hoá đơn có `Customer ID` 12346 (không phải c); không
  có bằng chứng giá sai (d) hay mua lặp lại (a).
- `lmdi-why` (d): cộng đúng và không phụ thuộc thứ tự. Thay lần lượt **cũng** cộng đúng (b sai); LMDI không phải
  luôn nhỏ hơn (a); nó cần doanh thu cả hai tháng (c).
- `dec-2011` (a): kỳ chưa đủ dữ liệu. Ngoại suy tuyến tính (d) bỏ qua mùa vụ trong tháng.
- `next-question` (a): nhánh đóng góp lớn nhất là hai hoá đơn không mã; hiểu chúng quyết định câu chuyện. Bỏ dòng
  không mã (d) làm mất 16.5% doanh thu khỏi báo cáo.
