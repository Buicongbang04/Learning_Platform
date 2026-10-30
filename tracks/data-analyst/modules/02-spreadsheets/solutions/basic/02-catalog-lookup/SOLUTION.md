# Lời giải: tra danh mục giá cho đơn hàng tháng 12/2011

Workbook lời giải: `catalog_lookup.xlsx` cùng thư mục.

## Công thức (hàng 2 của Orders)

| Cột | Công thức |
| --- | --- |
| G | `=XLOOKUP(D2,Catalog!$B$2:$B$4102,Catalog!$A$2:$A$4102,"NOT IN CATALOG")` |
| H | `=IFNA(VLOOKUP(D2,Catalog!$B$2:$C$4102,2,FALSE),"")` |
| I | `=HLOOKUP(C2,Regions!$B$1:$S$2,2,FALSE)` |
| J | `=E2*F2` |
| K | `=IF(H2="","",1-F2/H2)` |

Summary: `B2 =COUNTIF(Orders!G2:G1519,"NOT IN CATALOG")`, `B3 =COUNTIF(Orders!K2:K1519,">0")`,
`B4 =SUM(Orders!J2:J1519)`, `B5 =SUMIFS(Orders!J2:J1519,Orders!G2:G1519,"NOT IN CATALOG")`,
`B6 =SUMIFS(Orders!J2:J1519,Orders!I2:I1519,"EU")/B4`,
`B9 =INDEX(Catalog!$C$2:$C$4102,MATCH(B8,Catalog!$B$2:$B$4102,0))`.

`.xlsx` lưu `XLOOKUP` và `IFNA` thành `_xlfn.XLOOKUP`, `_xlfn.IFNA`; LibreOffice ghi `FALSE` thành `FALSE()`.

## Vì sao như vậy

- **Tra sang trái**: mã ở cột B, mô tả ở cột A. VLOOKUP chỉ trả cột bên phải khoá, nên Description cần
  XLOOKUP hoặc INDEX/MATCH. ListPrice nằm bên phải mã nên VLOOKUP dùng được, với `FALSE`.
- **Khớp gần đúng là bẫy**: Catalog sắp theo mô tả. VLOOKUP thiếu `FALSE` tìm nhị phân trên cột mã
  chưa sắp xếp và trả giá của mã khác. Không có `#N/A` nào báo động; chỉ đối chiếu mới thấy.
- **Không tìm thấy là thông tin**: 440/1 518 dòng (29.0%) là mã mới (phần lớn dải `23xxx` ra mắt năm
  2011), mang 17 297.98 / 46 188.59 GBP = **37.5% doanh thu**. Nhãn `"NOT IN CATALOG"` biến nó thành
  một con số trên báo cáo. `IFERROR(...,0)` sẽ giấu nó và còn làm DiscountPct lỗi chia cho 0.
- **Đọc kết quả**: trong 1 078 dòng có giá niêm yết, 260 dòng bán thấp hơn (trung vị thấp hơn 68.8%),
  706 dòng bằng, 112 dòng cao hơn. Chênh lệch so với giá niêm yết trên các dòng bán thấp hơn là 8 311.28
  GBP. Mức giảm phổ biến 60–80% không giống chiết khấu theo số lượng (vài chục %), giống giá đã đổi hoặc
  xả hàng cuối năm. Kết luận gửi Head of Sales là một **câu hỏi** cho team pricing, không phải "sales đang
  giảm giá 69%". Bài học tra cứu: bảng tham chiếu không có ngày hiệu lực là một ảnh chụp đã cũ.
- **HLOOKUP** hợp với bảng ngang copy từ slide; khách EU chiếm 1 397/1 518 dòng và 91.1% doanh thu.

## Đáp án trắc nghiệm

- `not-found-share` (c) **khoảng 37%** (37.5%). 29% là tỉ lệ **dòng**, không phải doanh thu: hàng mới
  có giá trị dòng cao hơn trung bình.
- `why-not-found` (b): danh mục là của năm trước. (a) sai vì G dùng XLOOKUP khớp chính xác; (c), (d) đã
  được loại khi dựng workbook (mã viết HOA, TRIM, cùng kiểu text).
- `iferror-zero` (b): giá 0 làm `1-F2/H2` chia cho 0, và tổng "giá niêm yết" bị kéo xuống.
- `below-list` (a).
- `discount-conclusion` (b): quan sát khác kết luận; (d) không trả lời được từ cột DiscountPct.
- `lookup-choice` (b): Excel 2016 hiện `#NAME?` với XLOOKUP; VLOOKUP không nhận số cột âm.
