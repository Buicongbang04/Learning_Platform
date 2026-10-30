# Lời giải: linter cho chart gây hiểu nhầm

## Cách làm

1. **`dual_axis`**: `twinx()` tạo một Axes thứ hai đặt đúng khung của Axes gốc. So
   `get_position().bounds` (làm tròn 6 chữ số) giữa mọi Axes của figure: có hai khung trùng nhau là có twin.
   Hai panel `subplots(1, 2)` có khung khác nhau nên không bị báo.
2. **`pie_too_many_slices`**: đếm `Wedge` trong `ax.patches`.
3. **`truncated_bar_axis`**: duyệt `ax.containers`, giữ `BarContainer` (cả `ax.hist` cũng sinh loại này,
   và histogram cũng phải từ 0). `orientation` cho biết trục giá trị; lấy `min` của `get_ylim()`/`get_xlim()`
   để không sai khi trục bị đảo (`invert_yaxis()` của funnel).
4. **`unsorted_bars`**: chỉ xét trục danh mục. `ax.bar(["SP", "RJ"], ...)` gắn `StrCategoryConverter`; trục
   ngày gắn converter khác nên bị loại; pandas `plot.bar()` không gắn converter mà ghi nhãn chữ lên vạch
   chia, nên kiểm nhãn vạch chia có chữ nào không đọc được thành số. Sắp các `Rectangle` theo vị trí rồi
   kiểm chiều cao đơn điệu theo một trong hai chiều (barh tăng dần từ dưới lên là "lớn nhất ở trên").
5. **`missing_axis_label`**: bỏ qua Axes có pie hoặc `axison = False`; với từng trục đang hiện
   (`get_visible()`, trục x của twin bị ẩn) và còn vạch chia, nhãn rỗng là lỗi. Trục đã `set_yticks([])` vì
   dùng nhãn trực tiếp thì không bị đòi nhãn.
6. **`honest_bar`**: kiểm tên trước (chart không đơn vị là chart chưa xong), `sort_values(ascending=False)`
   trên bản sao, vẽ nhãn chuỗi, `set_ylim(bottom=0)`, nhãn trục từ tên index và tên Series.

## Vì sao như vậy

- Linter kiểm **hình thức**, không hiểu **ngữ nghĩa**. Nó không biết thứ trong tuần có thứ tự, không biết
  tháng cuối mới có 9 ngày, không biết bạn đang so tổng hay trung bình. Vì thế đầu ra là "chỗ cần người
  nhìn", không phải phán quyết; mỗi luật có ngoại lệ hợp lý (bar theo thứ, dual axis °C/°F).
- Ngưỡng 6 lát pie và "từ 3 bar" là quy ước, không phải định luật. Điều quan trọng là luật nhất quán và
  được ghi ra, để cả team review chart theo cùng một chuẩn.

## Bốn chart thật

| Chart | Linter báo | Đọc lại |
| --- | --- | --- |
| 1. Điểm review TB theo phương thức thanh toán, trục từ khoảng 3.93 | `truncated_bar_axis` | debit_card 4.18, credit_card 4.09, boleto 4.09, voucher 3.95: chênh nhau nhiều nhất 0.23 điểm (thật ra gấp 1.06 lần), nhưng trên hình bar debit_card cao khoảng 12 lần bar voucher. debit_card chỉ có 1 471 đơn so với 75 882 đơn credit_card. Headline "hài lòng hơn hẳn" không đứng vững. |
| 2. Khách vãng lai (bar) và nhiệt độ (line) trên hai trục y | `dual_axis` | Tương quan theo tháng 0.87, nhưng tháng nóng nhất là 07/2011 còn tháng đông vãng lai nhất là 05/2012: hai năm có mức nền khác nhau (dịch vụ tăng trưởng) và mùa vụ trùng nhau. Hai panel chung trục x cho thấy điều đó; trục kép thì giấu. "Nhiệt độ quyết định" là kết luận nhân quả từ một tương quan có nhiễu mùa vụ. |
| 3. Pie doanh thu 27 bang | `pie_too_many_slices` | SP 37.5%, RJ 13.4%, MG 11.7%, RS 5.6%, PR 5.1%; 20 lát còn lại không đọc được. Bar ngang top 8 + "Khác". |
| 4. Số giao dịch theo phương thức, sắp A-Z, không nhãn trục | `missing_axis_label`, `unsorted_bars` | credit_card 76 795 (73.9%), boleto 19 784, voucher 5 775, debit_card 1 529 (và 3 giao dịch `not_defined`, không đủ cao để thấy). Đơn vị là **dòng thanh toán**, không phải đơn hàng: một đơn có thể trả bằng nhiều voucher; thiếu nhãn trục làm người xem hiểu nhầm đơn vị. |

## Đáp án trắc nghiệm

- `truncated-ratio` (c) **khoảng 3 lần**: trên hình là (4.2 − 3.9) / (4.0 − 3.9) = 3, dữ liệu là 1.05.
- `weekday-warning` (b): thứ là danh mục có thứ tự; sắp theo giá trị làm mất khả năng thấy "cuối tuần
  thấp". Đổi nhãn thành số (d) chỉ để qua mặt linter là che lỗi chứ không sửa.
- `dual-axis-fix` (b): hai panel chung trục x. (a) chính là cách dual axis "chứng minh" mọi thứ; (c) vẫn
  là một thang tự chọn; (d) không trả lời câu hỏi quan hệ.
- `many-states` (b): bar ngang, sắp giảm dần, gộp "Khác". Donut (c) có cùng vấn đề góc; bar A-Z (d) có đủ
  dữ liệu nhưng mắt phải tự xếp hạng 27 cột.
- `line-from-zero` (a): line mã hoá bằng vị trí và độ dốc. (c) sai: matplotlib tự co trục y của line về dải
  dữ liệu, chính vì thế bar mới cần được kiểm.
- `linter-blind-spot` (a): kỳ dở dang là lỗi ngữ nghĩa, không hình thức nào bắt được. (b) bị báo
  `truncated_bar_axis`, (c) bị báo `pie_too_many_slices`, (d) bị báo `unsorted_bars`.
