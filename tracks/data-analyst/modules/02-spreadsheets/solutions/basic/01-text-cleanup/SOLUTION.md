# Lời giải: làm sạch văn bản bằng hàm spreadsheet

Workbook lời giải: `text_cleanup.xlsx` cùng thư mục (đã lưu qua LibreOffice, có sẵn giá trị).

## Công thức (hàng 2, kéo xuống tới 301)

| Cột | Công thức |
| --- | --- |
| I | `=UPPER(TRIM(B2))` |
| J | `=PROPER(TRIM(C2))` |
| K | `=SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(H2,"EIRE","Ireland"),"RSA","South Africa"),"USA","United States")` |
| L | `=IF(LEFT(A2,1)="C","Cancel","Sale")` |
| M | `=IF(G2="","Guest",REPLACE(G2,3,2,"**"))` |
| N | `=CONCAT(A2,"-",I2)` (hoặc `=A2&"-"&I2`) |
| O | `=LOWER(SUBSTITUTE(TRIM(C2)," ","-"))` |
| P | `=IF(EXACT(C2,TRIM(C2)),0,1)` |

Summary: `B2 =SUM(Lines!P2:P301)`, `B3 =COUNTIF(Lines!L2:L301,"Cancel")`,
`B4 =COUNTIF(Lines!M2:M301,"Guest")`, `B5 =SUMPRODUCT(--NOT(EXACT(Lines!B2:B301,Lines!I2:I301)))`.

LibreOffice lưu `CONCAT` vào `.xlsx` thành `_xlfn.CONCAT`; test bỏ tiền tố này khi kiểm họ hàm.

## Vì sao như vậy

- **Thứ tự TRIM rồi PROPER/UPPER** không quan trọng về kết quả, nhưng TRIM phải có: 83/300 dòng (27.7%)
  có mô tả thừa khoảng trắng. Trên cả sheet `Year 2010-2011`, 885 trong 4 223 mô tả khác nhau đổi sau
  TRIM và chỉ còn 4 203 mô tả khác nhau, tức 20 sản phẩm đang bị đếm đôi chỉ vì dấu cách.
- **Mã hàng chữ thường** là vấn đề lớn hơn: 4 070 mã khác nhau còn 3 958 sau UPPER, 112 mã có cả hai
  dạng (`15056BL` 326 dòng, `15056bl` 62 dòng). Excel tra cứu không phân biệt hoa thường nên "chạy
  được", nhưng khi dữ liệu sang SQL/pandas, cùng một sản phẩm thành hai dòng trong báo cáo. Chuẩn hoá
  khoá trước, ở một cột riêng, rồi mọi tra cứu dùng cột đó.
- **PROPER chỉ để hiển thị**: nó viết hoa chữ sau mọi ký tự không phải chữ cái, nên ra `Poppy'S`,
  `Set Of4`, `T-Light`. Không dùng làm khoá.
- **REPLACE theo vị trí** để che dữ liệu cá nhân trước khi gửi file ra ngoài (masking); **SUBSTITUTE
  theo nội dung** để đổi tên. Lồng ba SUBSTITUTE chạy được với 3 mã; mapping dài hơn thì dùng bảng tra
  (bài basic 02) để business tự sửa.
- **EXACT** cho cột P vì `C2<>TRIM(C2)` cũng chạy được ở đây (chỉ khác khoảng trắng), nhưng ở B5 so mã
  gốc với mã viết HOA thì `=`/`<>` không phân biệt hoa thường và sẽ ra 0.
- **Giữ cột gốc**: dán dữ liệu tuần mới vào A:H, công thức I:P tự chạy lại; quy tắc sai thì sửa công
  thức. Find & Replace sửa đè thì không truy ngược được.

## Đáp án trắc nghiệm

- `spaces-count` (b) **83 dòng**. 17 là số mã hàng có chữ thường (B5), 95 là số dòng khách vãng lai (B4).
- `case-codes` (c) **3 958**: 112 mã có cả dạng hoa và thường. 117 là số mã có chữ thường, nhưng 5 mã
  chỉ xuất hiện ở dạng thường nên không bị gộp.
- `proper-quote` (b): PROPER viết hoa chữ `S` sau dấu nháy, kết quả chỉ hợp để hiển thị.
- `nbsp` (b): TRIM chỉ xử lý dấu cách mã 32; dùng `SUBSTITUTE(C2,CHAR(160)," ")` trước TRIM. Bộ Online
  Retail II không có ký tự này, dữ liệu copy từ web thì hay có.
- `substitute-vs-replace` (b): che mã không cần biết nội dung, chỉ cần vị trí; đổi `EIRE` cần tìm đúng chuỗi.
- `keep-raw` (a, b, d). (c) sai: cột phụ làm file lớn hơn chứ không nhỏ hơn, và đó không phải lý do.
