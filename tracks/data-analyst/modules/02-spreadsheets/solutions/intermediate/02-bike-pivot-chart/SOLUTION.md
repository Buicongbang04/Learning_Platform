# Lời giải: pivot table, bảng YoY và chart Bike Sharing

Workbook lời giải: `bike_pivot.xlsx` cùng thư mục (pivot `RentalsByMonth` trên sheet `Pivot`, chart
trên sheet `YoY`; dựng bằng LibreOffice và lưu `.xlsx`).

## Cách làm

1. `Days!M2 =YEAR(A2)`, kéo xuống.
2. Pivot: nguồn `Days!A1:M732`, Rows `mnth`, Columns `Year`, Data Sum of `cnt`.
3. `YoY!B2 =SUMIFS(Days!$L$2:$L$732,Days!$M$2:$M$732,2011,Days!$D$2:$D$732,A2)`, C2 tương tự với 2012,
   `D2 =C2/B2-1`; `B14 =SUM(B2:B13)`, `C14 =SUM(C2:C13)`, `D14 =C14/B14-1`.
4. Chart cột nhóm từ `YoY!B1:C13`, tiêu đề là kết luận (headline bên dưới).

## Kết quả

| Tháng | 2011 | 2012 | YoY |
| --- | --- | --- | --- |
| 1 | 38 189 | 96 744 | +153.3% |
| 2 | 48 215 | 103 137 | +113.9% |
| 3 | 64 045 | 164 875 | +157.4% |
| 4 | 94 870 | 174 224 | +83.6% |
| 5 | 135 821 | 195 865 | +44.2% |
| 6 | 143 512 | 202 830 | +41.3% |
| 7 | 141 341 | 203 607 | +44.1% |
| 8 | 136 691 | 214 503 | +56.9% |
| 9 | 127 418 | 218 573 | +71.5% |
| 10 | 123 511 | 198 841 | +61.0% |
| 11 | 102 167 | 152 664 | +49.4% |
| 12 | 87 323 | 123 713 | +41.7% |
| Cả năm | 1 243 103 | 2 049 576 | +64.9% |

Headline gợi ý: "2012 cao hơn 2011 ở cả 12 tháng, +64.9% cả năm; tăng mạnh nhất tháng 1–3 (+114% tới
+157%) khi nền 2011 còn thấp".

## Vì sao như vậy

- **Pivot để tìm câu chuyện, SUMIFS để báo cáo cố định**: pivot dựng trong vài giây, nhưng bố cục đổi
  khi ai đó kéo thêm trường, và không tự Refresh khi dữ liệu đổi. Bảng YoY bằng SUMIFS có ô cố định để
  tham chiếu và tự tính lại. Hai bảng ra cùng số là một kiểm tra chéo miễn phí.
- **YoY so cùng tháng năm trước**, không so tháng liền trước: tháng 12 thấp hơn tháng 9 vì mùa đông,
  không phải vì nhu cầu giảm (module 08 phần đọc chart).
- **D14 là tổng chia tổng**: trung bình 12 tỉ lệ tháng ra 76.5%, cao hơn 64.9% vì các tháng đầu năm
  (nền 2011 thấp, tỉ lệ cao) được tính ngang các tháng hè đông khách.
- **Tăng trưởng không đều**: tháng 1–3 tăng 114–157%, mùa hè 41–57%. Một phần là hệ thống còn mới năm
  2011 (nền thấp), một phần thời tiết; muốn tách cần thêm dữ liệu (số trạm, số xe), Bike Sharing không có.
- **Chart**: hai chuỗi cùng đơn vị nên một trục y từ 0; cột nhóm hoặc hai đường đều được. Pie, 3D, dual
  axis đều sai cho câu hỏi so sánh này.

## Đáp án trắc nghiệm

- `yoy-year` (b) **khoảng 65%** (64.9%).
- `yoy-month` (a): tháng 3 +157.4%, tháng 6 +41.3%.
- `avg-of-growth` (b): trung bình không trọng số của 12 tỉ lệ là 76.5%.
- `pivot-refresh` (b): công thức tự tính lại, pivot là ảnh chụp cho tới khi Refresh.
- `growth-story` (b): headline nói kết luận và giới hạn. (c) nhầm nguyên nhân, (d) dữ liệu chỉ có 2 năm.
- `chart-type` (b).
