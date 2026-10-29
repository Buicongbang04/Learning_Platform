# Lời giải: line, bar, heatmap, stacked trên Bike Sharing

## Cách làm

1. **`daily_rides`**: `pd.to_datetime(hour["dteday"])` gán vào biến riêng, rồi
   `hour["cnt"].groupby(day).sum()`. Không gán lại cột `dteday` của `hour`: hàm chuẩn bị dữ liệu không
   được có tác dụng phụ lên DataFrame của người gọi (các chart khác trong cùng notebook đang dùng nó).
2. **`rides_by_season`**: `groupby("season").cnt.sum()`, đổi index bằng `SEASON_LABELS`,
   `sort_values(ascending=False)`. Hàm trả **bảng xếp hạng**; chart thì `reindex` về thứ tự mùa vì mùa
   là category có thứ tự.
3. **`weekday_hour_matrix`**: `pivot_table(..., aggfunc="mean")` rồi `reindex` đủ `range(7)` ×
   `range(24)`. Ô thiếu để `NaN`: điền 0 là nói "giờ đó không ai thuê", một khẳng định dữ liệu không
   có.
4. **`casual_share_by_month`**: tháng lịch bằng `to_period("M").to_timestamp()`, tổng `casual` và
   `registered` theo tháng, chia mỗi dòng cho tổng dòng (`div(..., axis=0)`).

## Vì sao như vậy

- **Mỗi chart cần một hình dạng dữ liệu**: line cần chuỗi theo thời gian, bar cần một giá trị mỗi
  nhóm, heatmap cần ma trận rộng, stacked 100% cần tỉ trọng. Phần lớn công sức vẽ chart là bước
  chuẩn bị này; tách nó thành hàm thì test được và dùng lại được trong dashboard.
- **Trung bình, không phải tổng, trong heatmap**: 731 ngày bắt đầu thứ Bảy 1/1/2011 và kết thúc thứ
  Hai 31/12/2012, nên thứ Bảy, Chủ nhật, thứ Hai có 105 ngày, các thứ khác 104; thêm 165 giờ không có
  dòng nào. Tổng sẽ thưởng cho ô có nhiều lần xuất hiện hơn.
- **Stacked 100%**: câu hỏi là tỉ trọng. Stacked tuyệt đối để mùa vụ của tổng lượt (tháng 1 khoảng 38
  nghìn, tháng 9/2012 khoảng 219 nghìn) lấn át cơ cấu, và phần `casual` nằm trên các nền khác nhau
  nên không so được.
- **Bước 1 của quy trình đọc chart (nhãn và đơn vị)**: Readme của UCI ghi `1: spring, 2: summer, 3:
  fall, 4: winter`, nhưng dữ liệu cho thấy `season = 1` là 21/12–20/3, tức **mùa đông** thiên văn ở
  Washington DC; mỗi mã lệch đúng một mùa. Chart bar với nhãn gốc sẽ nói "mùa xuân ế nhất" trong khi
  thực tế là mùa đông. Trong báo cáo thật, đổi nhãn thành khoảng ngày (hoặc `winter`, `spring`,
  `summer`, `fall`) và ghi chú nguồn; trong bài này giữ nhãn gốc để test khớp tài liệu của bộ dữ liệu.

## Con số tham chiếu (bộ thật)

| Đại lượng | Giá trị |
| --- | --- |
| Số ngày, tổng lượt | 731, 3 292 679 |
| Tổng 2011 / 2012 | 1 243 103 / 2 049 576 (+64.9%) |
| Ngày cao nhất / thấp nhất | 15/9/2012: 8 714; 29/10/2012: 22 (bão Sandy) |
| `rides_by_season` | fall 1 061 129, summer 918 589, winter 841 613, spring 471 348 (cao/thấp = 2.25) |
| Giờ đông nhất | T2–T6: 17h; T7, CN: 13h; ô cao nhất thứ Ba 17h, 544 lượt/giờ |
| Tỉ trọng casual cao nhất / thấp nhất | 07/2011: 25.8%; 01/2011: 8.0% |

## Đáp án trắc nghiệm

- `weekend-peak-hour` **13h**: cuối tuần không có đỉnh đi làm, đông nhất giữa trưa (T7 385, CN 375
  lượt/giờ lúc 13h). 8h và 17h là hai đỉnh của ngày làm việc.
- `season-label` **21/12 tới 20/3**: cell kiểm tra cho thấy `season = 1` gồm tháng 1, 2, 20 ngày đầu
  tháng 3 và 11 ngày cuối tháng 12. "1/1 tới 31/3" là cách hiểu theo quý, sai ở cả hai đầu.
- `season-ratio` **2.3 lần**: 1 061 129 / 471 348 = 2.25.
- `casual-peak-month` **07/2011** (25.8%); 04/2011 đứng thứ hai (23.6%). Các tháng 2012 thấp hơn cùng
  kỳ 2011 dù số lượt casual tăng, vì thành viên tăng nhanh hơn: tỉ trọng giảm không có nghĩa là số
  lượng giảm.
- `yoy-growth` **+65%**.
- `why-100-stacked` (b): tổng lượt mỗi tháng khác nhau nhiều lần, nên trên stacked tuyệt đối phần
  casual nằm trên các nền khác nhau. Stacked 100% làm mọi cột cao bằng nhau, mắt chỉ so phần chia;
  đổi lại nó **mất** số tuyệt đối (c sai).
- `why-mean-heatmap` (a): xem phần "Vì sao". (d) sai vì tổng không ưu ái riêng cuối tuần.
- `season-bar-order` (c): mùa có thứ tự tự nhiên; sắp theo giá trị làm mất vòng mùa vụ. Thay vì
  sắp, tô màu nhấn mùa cao nhất.
