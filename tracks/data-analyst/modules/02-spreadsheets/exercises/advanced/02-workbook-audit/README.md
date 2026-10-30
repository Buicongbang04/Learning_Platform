---
title: Kiểm toán workbook báo cáo vận hành Bike Sharing - tìm, sửa và giải trình lỗi
level: advanced
services: []
files:
  - path: starter/ops_report.xlsx
    note: Workbook có lỗi cài sẵn ở sheet Report; sửa tại chỗ
  - path: starter/AUDIT.md
    note: Bảng lỗi, headline mới, cách phòng
  - path: tests/test_audit.py
    note: Không sửa
run:
  - libreoffice --calc tracks/data-analyst/modules/02-spreadsheets/exercises/advanced/02-workbook-audit/starter/ops_report.xlsx
  - uv run pytest tracks/data-analyst/modules/02-spreadsheets/exercises/advanced/02-workbook-audit -q
---

## Mục tiêu

Làm việc một DA senior hay phải làm mà ít ai dạy: nhận một workbook "đã chạy nhiều tháng" của người
khác, tìm lỗi bằng quy trình review có hệ thống, sửa tại chỗ, đo ảnh hưởng của từng lỗi lên con số đã
báo cáo, và viết lại headline đúng.

## Đề bài

Người làm trước để lại `starter/ops_report.xlsx`: báo cáo lượt thuê xe theo tháng 2011–2012 của Capital
Bikeshare (Bike Sharing, UCI, CC BY 4.0). Headline đã gửi ban giám đốc nằm ở `Report!A32`. Giám đốc vận
hành nghi số không khớp với dashboard và nhờ bạn kiểm.

- `Days`: toàn bộ 731 ngày của `day.csv` và cột `MonthStart` (đúng, không cần sửa).
- `Seasons`: bảng mã mùa theo UCI Readme (1 = spring, 2 = summer, 3 = fall, 4 = winter), sắp theo tên.
- `Report`: A2:A25 là 24 tháng; B `Rentals`, C `Days`, D `AvgPerDay`, E `CasualShare` (tỉ trọng lượt khách
  vãng lai trên tổng lượt), F `Season` của ngày đầu tháng, G `YoY` (G14:G25, so cùng tháng năm trước);
  B27:B30 tổng 2011, tổng 2012, lượt thuê trung bình mỗi ngày 2012, tăng trưởng 2012 so với 2011.

Việc cần làm:

1. Review mọi công thức của `Report` theo quy trình ở phần 6 lý thuyết. Có **ít nhất 6 lỗi**, thuộc các
   loại: số gõ đè công thức, vùng SUM thiếu, trung bình của trung bình, sai mẫu số, tra cứu khớp gần
   đúng, tham chiếu tuyệt đối sai chỗ.
2. Sửa **tại chỗ**, giữ nguyên bố cục, không gõ cứng số. Có thể thêm sheet `Checks` của riêng bạn.
3. Viết `starter/AUDIT.md`: bảng lỗi (ô/vùng, lỗi gì, ảnh hưởng trước → sau bằng số, cách sửa), headline
   mới có số đã sửa, 2–4 cách phòng lỗi lần sau.

## Tiêu chí đạt

- Test pass: mọi ô B2:F25, G14:G25, B27:B30 là công thức và đúng (tổng 2011 là 1 243 103, tổng 2012 là
  2 049 576, trung bình 2012 là 5 600 lượt/ngày, tăng 64.9%); B13 là SUMIFS.
- `AUDIT.md` không còn TODO, đủ ba mục, bảng lỗi ít nhất 6 dòng nhắc B13, B28, B29 và lỗi ở cột E, F, G;
  headline mới có con số %.
- Phần giải trình chấm theo rubric trong `SOLUTION.md` (100 điểm).

## Gợi ý

### Gợi ý 1

Bật View > Show Formula (Ctrl+` trong Excel). So từng cột với ô ngay trên và ngay dưới: công thức phải
"cùng hình dạng", chỉ khác số hàng. Ô nào khác hình dạng hoặc là số thì đáng ngờ.

### Gợi ý 2

Trước khi sửa, chép giá trị cũ của các ô kết quả (B27:B30, vài ô E, F, G) ra chỗ khác để ghi "trước →
sau" trong AUDIT.md. Kiểm lại bằng một đường tính độc lập: `SUM(Days!L2:L732)` phải bằng B27 + B28, và
pivot `mnth` × năm của bài intermediate 02 cho cùng số theo tháng.
