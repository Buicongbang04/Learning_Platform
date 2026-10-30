# Lời giải: chọn chart và công cụ theo tình huống

## Cách làm

Mỗi câu đi qua hai bước giống nhau, đúng như phần 2 và phần 7 của lý thuyết:

1. Viết câu hỏi của stakeholder thành một câu có động từ so sánh, rồi xếp vào một trong sáu loại:
   so sánh, xu hướng, phân phối, thành phần, quan hệ, luồng.
2. Lấy chart mặc định của loại đó, rồi xét điều kiện phụ (bao nhiêu nhóm, có thứ tự không, một thời
   điểm hay theo thời gian).

Với công cụ: ai xem, xem bao nhiêu lần, có cần tự cắt lát, có cần tái lập, công ty đang ở hệ sinh
thái nào.

## Đáp án từng câu

| Câu | Đáp án | Loại câu hỏi / tiêu chí quyết định |
| --- | --- | --- |
| `late-deliveries-trend` | b. Line chart theo tuần | Xu hướng |
| `provinces-revenue` | c. Bar ngang sắp giảm dần, top 15 + "Khác" | So sánh, nhiều nhóm không có thứ tự |
| `delivery-time-shape` | d. Histogram (trục log nếu đuôi dài) | Phân phối một biến số |
| `channel-mix` | a. Stacked bar 100% theo tháng | Thành phần theo thời gian |
| `new-vs-returning` | b. Một con số lớn, hoặc pie 2 lát | Thành phần, 2 phần, một thời điểm |
| `ads-vs-orders` | c. Scatter chi phí vs số đơn | Quan hệ hai biến số |
| `support-shifts` | a. Heatmap thứ × giờ | Hai chiều phân loại + một số |
| `checkout-steps` | d. Funnel, % so với bước trước | Luồng / chuyển đổi |
| `tool-weekly-kpi` | b. Power BI + row-level security | Nhiều người, hằng tuần, phân quyền, Microsoft 365 |
| `tool-board-slide` | a. matplotlib trong script/notebook ở git | Một lần, ảnh tĩnh, phải tái lập |
| `tool-interactive-share` | c. plotly xuất HTML | Cần tương tác, chưa có BI |
| `tool-finance-scenario` | d. Excel/Google Sheets | Người nhận cần sửa số, dùng một lần, ít dòng |

### `late-deliveries-trend`: line chart

"Có đang giảm không" là câu hỏi **xu hướng**: trục x là thời gian, một chuỗi, 78 điểm. Line mã hoá
bằng vị trí và độ dốc nên mắt thấy ngay hướng đi. Bar 78 cột vẫn đọc được nếu giữ thứ tự thời gian,
nhưng phương án (a) **sắp giảm dần** làm mất trục thời gian, nên không còn trả lời được câu hỏi. Pie
tỉ trọng từng tuần vô nghĩa (78 lát, và tỉ lệ trễ không cộng lại thành một tổng). Histogram (d) cho
biết tỉ lệ trễ thường nằm ở khoảng nào nhưng xoá thứ tự thời gian, đúng thứ cần thấy.

### `provinces-revenue`: bar ngang sắp giảm dần, top 15 + "Khác"

**So sánh** giữa 34 nhóm **không có thứ tự tự nhiên**: sắp theo giá trị để thấy ngay ai dẫn đầu, ai
tụt lại. Nhiều nhóm thì bar **ngang** để tên tỉnh đọc được không phải xoay chữ; gộp đuôi thành
"Khác" để chart không dài quá một slide (danh sách đủ 34 tỉnh để ở phụ lục hoặc bảng). Thứ tự mã tỉnh
(a) là thứ tự không ai quan tâm. Pie 34 lát (b) là lỗi kinh điển: mắt so góc kém, lát nhỏ không đọc
được. Heatmap tỉnh × tháng (d) trả lời câu hỏi khác (mùa vụ theo tỉnh) và đọc màu kém chính xác hơn
đọc độ dài.

### `delivery-time-shape`: histogram

"Đa số mất bao lâu, có đuôi dài không" là câu hỏi **phân phối** của một biến số. Histogram cho thấy
đỉnh, độ rộng và đuôi. Thời gian giao hàng gần như luôn lệch phải (vài đơn kẹt nhiều ngày), nên
thường cần thêm trục log hoặc ECDF để thấy đuôi. Bar một cột trung bình (b) giấu hết hình dạng và
còn bị đuôi kéo lệch. Line hay scatter theo mã đơn (a, c) đặt một trục vô nghĩa: mã đơn không phải
biến cần hiểu.

### `channel-mix`: stacked bar 100% theo tháng

**Thành phần** của tổng **theo thời gian**, 4 phần. Câu hỏi là **tỉ trọng** chứ không phải quy mô,
nên dùng bản 100% (mọi cột cao bằng nhau, mắt chỉ so phần chia). Nếu CMO hỏi cả quy mô, thêm một
line tổng doanh thu riêng phía trên. 12 pie (b) buộc người xem so góc giữa 12 hình. Line doanh thu
tuyệt đối (c) không cho thấy tỉ trọng: cả 4 kênh cùng tăng vào mùa cao điểm thì 4 đường cùng đi lên
dù tỉ trọng không đổi. Scatter hai kênh (d) trả lời câu hỏi quan hệ, bỏ mất 2 kênh.

### `new-vs-returning`: một con số lớn, hoặc pie 2 lát

Thành phần **2 phần, một thời điểm**, một ý duy nhất cho slide: đây là trường hợp hiếm mà pie chấp
nhận được, và một con số lớn ("38% khách tháng này là khách mới") thường còn tốt hơn. Stacked bar
12 tháng (a) và line theo ngày (d) trả lời câu hỏi xu hướng mà slide không hỏi; histogram số đơn mỗi
khách (c) là câu hỏi phân phối khác hẳn.

### `ads-vs-orders`: scatter

**Quan hệ** giữa hai biến số, mỗi ngày một điểm: scatter, có thể thêm đường xu hướng và tô màu theo
mùa (vì mùa cao điểm vừa tăng chi quảng cáo vừa tăng đơn, đây là biến gây nhiễu như ví dụ nhiệt độ ở
phần 4 lý thuyết). Dual axis (a) là bẫy: hai thang tự chọn nên ai vẽ cũng "thấy" hai đường đi cùng
nhau. Stacked bar (b) cộng chi phí với số đơn, hai đại lượng khác đơn vị. Heatmap thứ × tháng (d)
cho thấy mùa vụ của chi phí, không trả lời quan hệ.

### `support-shifts`: heatmap thứ × giờ

**Hai chiều phân loại** (7 thứ × 24 giờ) và một số: heatmap. Câu hỏi xếp ca cần **pattern** (khung
giờ đông của từng ngày), đúng thế mạnh của heatmap; cần con số chính xác thì in giá trị trong ô.
Pie 168 lát (b) không đọc được. Một line 168 điểm liên tục (c) vẫn có thông tin nhưng mắt phải tự
cắt thành 7 đoạn để so cùng giờ giữa các ngày. Histogram gộp mọi thứ (d) mất cả thứ lẫn thứ tự giờ.

### `checkout-steps`: funnel, ghi % so với bước trước

**Luồng / chuyển đổi** qua các bước có thứ tự: funnel (thực chất là bar ngang giữ thứ tự bước). Câu
hỏi "rơi nhiều nhất ở bước nào" cần tỉ lệ **so với bước trước**, và nên ghi cả số khách mất tuyệt
đối, vì hai cách hiểu "rơi nhiều nhất" có thể chỉ hai bước khác nhau (phần 6 lý thuyết). Pie (a) coi
4 bước như 4 phần rời nhau của một tổng, sai bản chất (khách ở bước 4 cũng nằm trong bước 1). Line theo
ngày (b) là câu hỏi xu hướng; scatter (c) không có thứ tự bước.

### `tool-weekly-kpi`: Power BI + row-level security

Nhiều người xem, **hằng tuần**, mỗi người **tự lọc** và **chỉ được thấy vùng mình**: cần BI có phân
quyền theo dòng. Công ty đã dùng Microsoft 365 nên Power BI rẻ và tích hợp sẵn (Tableau, Looker cũng
làm được nhưng thêm license/hệ sinh thái). 40 ảnh PNG mỗi tuần (a) là việc thủ công không ai muốn
duy trì và không cho tự lọc. Excel qua email (c) không phân quyền được (ai cũng mở được mọi sheet) và
số dễ lệch giữa các bản. Một HTML plotly cho cả 40 người (d) cũng lộ số của mọi vùng.

### `tool-board-slide`: matplotlib trong script/notebook lưu ở git

Một chart, **ảnh tĩnh** cho slide, **phải vẽ lại** khi số chốt lại, và người hỏi "con số này tính thế
nào" ba tháng sau cần câu trả lời: sinh từ code trong git. matplotlib cho kiểm soát từng chi tiết
(headline, nhãn trực tiếp, màu nhấn). Dựng dashboard Tableau cho một chart (b) là quá tay. plotly
HTML (c) sai môi trường: slide trình chiếu không tương tác, và tương tác làm người xem tự tìm kết
luận khác. Copy-paste vào PowerPoint (d) không tái lập được và dễ sai.

### `tool-interactive-share`: plotly xuất HTML

Người xem cần **rê chuột** xem từng ngày (730 điểm, không ghi nhãn hết được) và công ty chưa có BI:
plotly xuất một tệp HTML tự chứa, mở được trong trình duyệt. Ảnh PNG (a) không tương tác. Excel kèm
730 dòng (b) mở được nhưng PM phải tự dò bảng. Mua license Tableau cho một chart (d) không cân xứng.

### `tool-finance-scenario`: Excel/Google Sheets

Người nhận cần **tự sửa giả định** và thấy chart đổi ngay, dữ liệu nhỏ (2 000 dòng), dùng một lần:
đúng chỗ mạnh của spreadsheet. Điểm yếu (khó tái lập, dễ sai do copy-paste) ít quan trọng vì không
dùng lại hằng tuần; vẫn nên để giả định ở một vùng ô riêng, có ghi chú. Script matplotlib (a) bắt kế
toán gửi lại cho DA mỗi lần đổi số. Metabase (b) dành cho số đã nằm trong warehouse và nhiều người
xem, không cho người xem sửa giả định. Cài notebook trên máy kế toán (c) bắt họ học công cụ mới cho
một việc Excel đã làm được.
