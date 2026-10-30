---
title: Báo cáo doanh thu tuần cho khách quốc tế, có sheet kiểm lỗi tự động
level: advanced
services: []
files:
  - path: starter/weekly_report.xlsx
    note: Tự thiết kế cột phụ; điền Weekly, Checks, Notes
  - path: tests/test_weekly_report.py
    note: Không sửa
run:
  - libreoffice --calc tracks/data-analyst/modules/02-spreadsheets/exercises/advanced/01-weekly-report-checks/starter/weekly_report.xlsx
  - uv run pytest tracks/data-analyst/modules/02-spreadsheets/exercises/advanced/01-weekly-report-checks -q
---

## Mục tiêu

Dựng một báo cáo tuần bằng spreadsheet ở chuẩn có thể gửi lãnh đạo mỗi tuần: tự thiết kế cột phụ, tính
đúng các metric có bẫy (đếm hoá đơn và khách khác nhau, AOV, WoW), thêm sheet kiểm tra tự báo khi số
sai, và viết ghi chú ngắn đọc số cho stakeholder.

## Đề bài

Head of International Sales muốn mỗi thứ Hai nhận một file: doanh thu, số đơn, số khách, AOV và tăng
trưởng so với tuần trước của khách ngoài Anh, kèm vài dòng nhận xét. Bạn làm bản đầu tiên cho 5 tuần
31/10–04/12/2011 trên `starter/weekly_report.xlsx` (Online Retail II, CC BY 4.0): sheet `Data` có 6 729
dòng gốc, **kể cả** đơn huỷ, dòng điều chỉnh và dòng trùng lặp.

1. Thêm cột phụ ở `Data` từ cột I trở đi (tự thiết kế), không sửa 8 cột gốc.
2. Sheet `Weekly` (bố cục cố định, test đọc đúng ô):
   - B2:B6 doanh thu (định nghĩa chung: dòng hợp lệ, `Quantity * Price`); C2:C6 số đơn (hoá đơn không
     huỷ có ít nhất một dòng hợp lệ); D2:D6 số khách (Customer ID khác trống, có ít nhất một dòng hợp lệ
     trong tuần); E2:E6 AOV; F3:F6 WoW doanh thu (F2 để trống).
   - Dòng 7: B7, C7 tổng; **D7 là số khách khác nhau trong cả 5 tuần**; E7 AOV của 5 tuần.
3. Sheet `Checks`, mỗi ô là công thức:
   B2 tổng doanh thu Weekly khớp tổng doanh thu dòng hợp lệ của Data (TRUE/FALSE, so với `Weekly!`);
   B3 tổng số đơn Weekly khớp số hoá đơn hợp lệ khác nhau của Data (TRUE/FALSE, so với `Weekly!`);
   B4 mọi dòng Data nằm trong 5 tuần (TRUE/FALSE); B5 số dòng bị loại khỏi doanh thu; B6 số dòng trùng
   lặp hoàn toàn (giống một dòng phía trên ở cả 8 cột; báo ra, không xoá); B7 `ALL OK` = AND các ô
   TRUE/FALSE.
4. Sheet `Notes` ô A2: 3–6 câu cho Head of International Sales: tuần nào bất thường, vì sao (drill-down
   theo quốc gia/khách), số nào cần lưu ý về chất lượng dữ liệu, việc tiếp theo.

Thêm conditional formatting, data validation, chart là điểm cộng theo rubric, không bắt buộc cho test.

## Tiêu chí đạt

- Test pass: Weekly đúng từng tuần (tuần 14/11: 56 727.46 GBP, 87 đơn, 64 khách), dòng 7 đúng (198 855.47
  GBP, 314 đơn, 176 khách khác nhau), Checks B2:B4 và B7 ra TRUE, B5 = 209, B6 = 24, các ô là công thức,
  B2/B3 tham chiếu sheet Weekly; Notes có ít nhất 40 từ và có số.
- Nội dung chấm theo rubric trong `SOLUTION.md` (100 điểm): độ đúng, thiết kế workbook, kiểm tra, ghi chú.

## Gợi ý

### Gợi ý 1

Tuần bắt đầu thứ Hai: `=INT(E2)-WEEKDAY(E2,2)+1`. Cờ "dòng hợp lệ đầu tiên của hoá đơn" và "lần đầu
khách xuất hiện trong tuần" làm bằng COUNTIFS trên vùng **mở rộng dần** (`A$1:A1`), ví dụ
`=IF(I2=0,0,IF(COUNTIFS(A$1:A1,A2,I$1:I1,1)=0,1,0))`. Sau đó Weekly chỉ là SUMIFS trên các cờ.

### Gợi ý 2

Dòng trùng: ghép 8 cột thành một khoá (`CONCAT`, ngày qua `TEXT(E2,"yyyy-mm-dd hh:mm")`), rồi đếm khoá
đã xuất hiện ở phía trên. Tránh `COUNTIF` trên khoá có mô tả sản phẩm: ký tự `*`, `?` trong text bị hiểu
là wildcard; `SUMPRODUCT(--(N$1:N1=N2))` so chính xác. Khi viết Notes, tách doanh thu tuần bất thường
theo quốc gia và theo hoá đơn trước khi gọi đó là "xu hướng".
