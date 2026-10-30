# Lời giải: kiểm toán workbook báo cáo vận hành

Bài advanced không có workbook lời giải; dưới đây là danh sách lỗi, cách sửa, số tham chiếu và rubric.
Bản sửa tham chiếu đã chạy qua test (4/4 pass).

## Các lỗi cài sẵn

| # | Ô / vùng | Lỗi | Ảnh hưởng (trước → sau) | Sửa |
| --- | --- | --- | --- | --- |
| 1 | B13 | Số 102167 (lượt thuê tháng 11/2011) dán đè lên công thức tháng 12/2011 | Tháng 12/2011 102 167 → 87 323; tổng 2011 1 257 947 → 1 243 103; D13 3 296 → 2 817 lượt/ngày | `=SUMIFS(Days!$L$2:$L$732,Days!$M$2:$M$732,A13)` |
| 2 | B28 | `SUM(B14:B24)` thiếu tháng 12/2012 | Tổng 2012 1 925 863 → 2 049 576 | `=SUM(B14:B25)` |
| 3 | B29 | `AVERAGE(D14:D25)`, trung bình của 12 trung bình tháng | 5 596 → 5 600 lượt/ngày | `=B28/SUM(C14:C25)` |
| 4 | E2:E25 | Mẫu số là `registered` thay vì tổng lượt: ra tỉ lệ casual/registered, không phải tỉ trọng | Tháng 5/2011 29.6% → 22.9%; tháng 1/2011 8.8% → 8.0%; cả 2012 22.2% → 18.2% | Mẫu số `B2` |
| 5 | F2:F25 | `VLOOKUP` thiếu `FALSE` trên bảng Seasons sắp theo tên (mã 3, 1, 2, 4) | Tháng 4–6 của cả hai năm `#N/A` → `summer`; các mã 1, 3, 4 tình cờ ra đúng, nên lỗi chỉ lộ ở 6 ô | `VLOOKUP(...,FALSE)` |
| 6 | G14:G25 | `=B14/$B$2-1`: mọi tháng 2012 so với tháng 1/2011 | Tháng 12/2012 +223.9% → +41.7%; tháng 6/2012 +431.1% → +41.3% | `=B14/B2-1` kéo xuống |
| 7 | B30 | Công thức đúng nhưng nhận B27, B28 sai | +53.1% → +64.9% | Tự đúng sau lỗi 1, 2 |

Headline cũ: "2012 tăng 53% so với 2011, trung bình 5 596 lượt/ngày, khách vãng lai chiếm khoảng 22% lượt
thuê năm 2012". Headline mới: **"Lượt thuê 2012 tăng 64.9% so với 2011 (2 049 576 lượt, trung bình 5 600
lượt/ngày); khách vãng lai chiếm 18.2%"**.

Ghi chú thêm (điểm cộng): nhãn mùa theo UCI (1 = spring) không khớp lịch thực tế của dữ liệu: ngày đầu
tháng 1 có `season = 1` nhưng là mùa đông ở Washington DC (module 08 có lưu ý này). Không phải lỗi công
thức, nhưng báo cáo hiển thị "spring" cho tháng 1 sẽ gây hiểu nhầm; nên ghi chú hoặc đổi sang quý.

## Vì sao những lỗi này nguy hiểm

- **Lỗi 1, 2** đi thẳng vào con số lãnh đạo nhớ (tăng trưởng năm), và không sinh ra ô lỗi nào. Chỉ Show
  Formulas hoặc đối chiếu tổng (`SUM(Days!L:L)` = B27 + B28) mới bắt được.
- **Lỗi 3** ảnh hưởng nhỏ ở đây (các tháng dài gần bằng nhau) nhưng sai về phương pháp; trên dữ liệu
  có nhóm kích thước rất khác nhau (AOV theo quốc gia), sai số lớn.
- **Lỗi 4** có số nhìn hợp lý (8–30%), không ai nghi; sai 4 điểm phần trăm trên tỉ trọng khách vãng lai
  đủ đổi quyết định ngân sách marketing cho nhóm khách này.
- **Lỗi 5** một phần lộ ra (`#N/A`), phần còn lại im lặng.
- **Lỗi 6** cho số vô lý (+431%) nhưng người đọc báo cáo hay bỏ qua cột YoY nếu headline không nhắc tới.

## Cách phòng

- Thêm sheet `Checks`: `=SUM(Report!B2:B25)=SUM(Days!L2:L732)`, `=B27+B28=SUM(Days!L2:L732)`,
  `=SUMPRODUCT(--ISERROR(Report!B2:G25))=0`, `ALL OK` ở đầu Report.
- Công thức cùng hình dạng trên cả cột; khoá sheet Report trừ ô đầu vào để không ai dán đè.
- Bảng tra cứu sắp theo khoá hoặc luôn dùng khớp chính xác; tỉ lệ dòng tổng = tổng tử / tổng mẫu.
- Review bởi người thứ hai với checklist trước khi gửi số ra ngoài team; số chính đối chiếu bằng pandas/SQL.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Tìm lỗi | 30 | Đủ 6 lỗi chính (5 điểm mỗi lỗi); nêu được B30 sai do lan truyền (điểm cộng ghi chú mùa không quá 100) |
| Sửa đúng | 25 | Toàn bộ test workbook pass, công thức cùng hình dạng, không số gõ tay |
| Đo ảnh hưởng | 20 | Mỗi lỗi có số trước → sau; chỉ ra lỗi nào đổi headline (1, 2, 4) và lỗi nào chỉ đổi chi tiết |
| Headline và giao tiếp | 15 | Headline mới đúng số; một câu giải thích cho ban giám đốc vì sao số đổi, không đổ lỗi cá nhân |
| Phòng lỗi | 10 | Đề xuất cụ thể, làm được ngay (Checks có công thức, khoá ô, checklist review) |

Trừ điểm: sửa bằng cách gõ cứng số đúng (−10 mỗi ô, test cũng FAIL); xoá hàng/cột làm đổi bố cục (−5);
headline mới không nêu khách vãng lai đã sửa (−3).
