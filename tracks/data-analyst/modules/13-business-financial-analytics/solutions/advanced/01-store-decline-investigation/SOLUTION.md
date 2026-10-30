# Hướng làm: điều tra 33 cửa hàng giảm doanh số

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết ba hàm, chuỗi điều tra với con số tham chiếu, các
quyết định cần cân nhắc và rubric chấm memo.

## Ba hàm

- **`store_yoy`**: lọc từng kỳ bằng `(Date >= start) & (Date <= end)`, `groupby("Store")` tổng `Sales`, `Open`,
  `Customers`; `join(how="inner")` để chỉ giữ cửa hàng có ở cả hai kỳ. Tập cửa hàng ở đây chọn theo **hai kỳ so
  sánh**, không theo toàn khoảng `train` như `comparable_stores` của bài Intermediate 02: 180 cửa hàng thiếu dữ liệu
  7-12/2014 vẫn đủ cả hai nửa đầu năm nên vẫn được so. Cách chọn nào cũng phải ghi rõ trong memo, vì nó quyết định
  "chuỗi tăng 3.4%" là tăng của tập cửa hàng nào. Ba thành phần là phân rã nhân, nên tích
  `(1 + days)(1 + traffic)(1 + spc)` đúng bằng `1 + growth` (khác với LMDI của module 01 vốn chia thay đổi tuyệt đối).
- **`competition_timing`**: dựng ngày mở từ năm và tháng (`pd.to_datetime` với dict `year`, `month`, `day`), điền
  tạm giá trị cho dòng thiếu rồi gán `unknown` bằng `np.select`, điều kiện xếp theo thời gian.
- **`group_growth`**: `join` nhãn vào bảng (`how="inner"`), `groupby` với tổng, median và tỉ lệ `growth < −0.10`;
  tăng trưởng gộp = tổng sales1 / tổng sales0 − 1, không phải trung bình của các tỉ lệ.

## Chuỗi điều tra và con số tham chiếu

| Bước | Con số |
| --- | --- |
| Con số báo cáo | 1 115 cửa hàng; H1/2015 so với H1/2014 **+3.35%**; 33 cửa hàng giảm > 10% (nhiều nhất: 91 −31.5%, 815 −27.1%, 629 −23.1%) |
| So được không | 180 cửa hàng thiếu dữ liệu 7-12/2014 nhưng đủ cả hai kỳ H1, nên so H1 với H1 vẫn được; nếu so cả năm thì không |
| Phân rã 33 cửa hàng | 30 cửa hàng mất > 10% lượt khách mỗi ngày (median −17.0%); chi tiêu mỗi khách median +1.1%, thấp nhất −4.7%; chỉ cửa hàng 674 ít ngày mở cửa hơn (148 → 115) |
| Đóng cửa dài ngày | 674 đóng liền 16/02 tới 25/03/2015 (growth −17.3%, spc +9%); 644 (23/02-19/03) và 699 (19/01-04/02) cũng đóng 2-4 tuần, giảm 5.5% và 9.3%, dưới ngưỡng 10% |
| Đối thủ theo thời điểm mở | during_p0 (31 cửa hàng) **−4.2%**, between (39) **−3.9%**, during_p1 (27) +1.3%, after_p1 (11) +2.4%, before_p0 (653) **+3.8%**, unknown (354) +4.3% |
| Trong 33 cửa hàng | between 9, during_p0 7, during_p1 2 (18 có đối thủ mới); before_p0 11; unknown 4 |
| Khoảng cách (đối thủ mở 2014 tới 06/2015) | < 500 m: 20 cửa hàng, median **−5.8%**; 500 m - 2 km: 29, −4.4%; > 2 km: 48, +1.8% |
| Chưa giải thích | 14 cửa hàng (đối thủ cũ hoặc không rõ, không đóng cửa). Doanh số theo tháng tụt thành bậc: 113 và 815 từ 05/2014, 1086 từ 08/2014, 91 từ 10/2014, rồi đứng yên |
| Dữ liệu lỗi | 354 cửa hàng thiếu ngày mở của đối thủ; cửa hàng 815 ghi năm 1900 |

**Câu chuyện đúng**: cửa hàng giảm vì **mất khách**, không phải vì giá hay giỏ hàng. Hơn một nửa (18/33) có đối thủ
mới trong 18 tháng qua; nhóm này giảm khoảng 4% trong khi nhóm đối chứng tăng khoảng 4%, và đối thủ càng gần càng
đau. 14 cửa hàng có cú tụt thành bậc trong 2014 mà dữ liệu không giải thích: việc của quản lý vùng.

Headline mẫu: **"18 trong 33 cửa hàng giảm hơn 10% có đối thủ mới mở từ 2014; 14 cửa hàng chưa rõ lý do cần kiểm
tại chỗ"**. Chart mẫu: (1) bar ngang tăng trưởng gộp theo nhóm thời điểm đối thủ mở, đường tham chiếu là tăng trưởng
chuỗi; (2) small multiples doanh số tháng của 4 cửa hàng chưa giải thích, cho thấy cú tụt thành bậc; (3) bar ba
thành phần (ngày mở cửa, khách, chi tiêu mỗi khách) của nhóm 33 cửa hàng.

## Các quyết định cần cân nhắc

- **Nhóm đối chứng**: so nhóm đối thủ mới với nhóm đối thủ từ trước 2014, không với "toàn chuỗi" (đã gồm nhóm bị
  ảnh hưởng). Đây vẫn là so sánh quan sát: cửa hàng có đối thủ mới có thể ở khu đang phát triển, nên ghi trong Giới
  hạn.
- **Ngưỡng 10%**: một ngưỡng cố định trên tăng trưởng bỏ sót cửa hàng giảm 8% có đối thủ mới; báo cáo nên kèm phân
  phối, không chỉ danh sách vượt ngưỡng.
- **Phân rã nhân hay cộng**: phân rã nhân (ngày × khách × giỏ) trả lời "thành phần nào đổi" rõ nhất cho từng cửa
  hàng; muốn đổi ra tiền thì dùng LMDI như module 01.
- **Khi nào dừng phân tích**: với 14 cửa hàng tụt thành bậc, thêm phân tích không thay được một cuộc gọi cho quản
  lý cửa hàng. Memo tốt nói rõ phần nào dữ liệu đã trả lời, phần nào cần người ở hiện trường.
- **Hành động khác nhau theo nhóm**: đối thủ mới là thay đổi cấu trúc (điều chỉnh mục tiêu, thử chương trình giữ
  khách có đối chứng); đóng cửa là tạm thời (tách khỏi like-for-like); chưa rõ thì điều tra tại chỗ.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Kiểm con số | 10 | Xác nhận hai kỳ so được (cửa hàng thiếu dữ liệu, đóng cửa), nói tăng trưởng chuỗi và số cửa hàng giảm |
| Phân rã | 20 | Tách ngày mở cửa, lượt khách, chi tiêu mỗi khách; kết luận "mất khách" có số |
| Nguyên nhân có đối chứng | 25 | Nhóm theo thời điểm đối thủ mở, so với nhóm đối thủ cũ; có thêm một bằng chứng liều-đáp ứng (khoảng cách) hoặc tương đương |
| Phần chưa giải thích | 15 | Tách được cửa hàng không có lời giải thích, có bằng chứng (doanh số theo tháng), không gán đại nguyên nhân |
| Memo | 20 | Headline trả lời thẳng; hành động khác nhau theo nhóm, có người làm và thời điểm xem lại; chart có tiêu đề kết luận |
| Giới hạn | 10 | Nêu ít nhất hai giới hạn cụ thể (so sánh quan sát, dữ liệu đối thủ thiếu / sai, chỉ đối thủ gần nhất) |

Từ 70 điểm trở lên là memo có thể mang vào buổi họp vùng.

## Sai lầm hay gặp

- Báo "các cửa hàng này bán kém" và đề xuất khuyến mãi cho cả 33, không tách nguyên nhân.
- So nhóm đối thủ mới với toàn chuỗi thay vì nhóm đối chứng.
- Dùng trung bình tăng trưởng của các cửa hàng làm tăng trưởng nhóm (cửa hàng nhỏ được trọng số như cửa hàng lớn).
- Coi năm 1900 hoặc ô trống là "đối thủ từ rất lâu" mà không ghi chú.
- So cả năm 2015 với 2014: 180 cửa hàng thiếu nửa sau 2014 làm số so sánh sai.
