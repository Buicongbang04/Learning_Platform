# Hướng làm: đánh giá chương trình khuyến mãi

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hai hàm, con số tham chiếu, các quyết định cần
cân nhắc và rubric chấm memo.

## Hai hàm

- **`promo_lift`**: lọc `Open == 1`, `Sales > 0`, `DayOfWeek` 1..5; `groupby([by, "Promo"])` lấy trung bình
  `Sales`, `Customers` và số ngày, `unstack("Promo")`; lift là tỉ số trung bình trừ 1. `spc_lift = (1 + sales_lift) /
  (1 + customers_lift) − 1` (chi tiêu mỗi khách tính bằng tỉ số của trung bình, không phải trung bình của tỉ số).
  Khi `by=None` thêm một cột hằng để dùng chung đường code.
- **`breakeven_discount`**: lợi nhuận gộp ngày khuyến mãi S1 − (1 − m)(1 + d)S1 bằng mS0 với S1 = (1 + L)S0, giải ra
  d* = mL / ((1 + L)(1 − m)). Test kiểm cả công thức lẫn định nghĩa.

## Con số tham chiếu

| Phân tích | Kết quả |
| --- | --- |
| Dashboard (mọi ngày mở cửa có bán) | +38.8% |
| Thứ Hai - thứ Sáu | doanh số **+38.79%**, lượt khách **+19.77%**, chi tiêu mỗi khách **+15.88%**; 376 875 / 319 818 ngày-cửa hàng |
| Vì sao hai số gần nhau | ngày thường không khuyến mãi gồm cả thứ Bảy (TB 5 875, thấp) và Chủ nhật (8 225, chỉ ít cửa hàng mở, cao): hai lệch bù nhau. Theo từng thứ, lift khác nhau rất nhiều |
| Theo thứ | T2 +57.1%, T3 +44.8%, T4 +36.8%, T5 +32.1%, T6 +22.1%; lượt khách +27% → +12%, giỏ +24% → +9% |
| Theo loại cửa hàng | a +37.7%, b **+20.0%**, c +39.5%, d +42.2% |
| Theo danh mục | a +40.8%, b **+11.5%** (9 cửa hàng, đều loại b), c +37.4% |
| Cuối tuần | thứ Bảy của tuần khuyến mãi +2.65%, Chủ nhật −2.21% so với tuần thường |
| Theo tuần (934 cửa hàng đủ ngày) | tuần khuyến mãi +36.2% so với tuần thường |
| Tuần thường sau tuần thường | chỉ 2 tuần (30/12/2013, 29/12/2014, lễ cuối năm): không đủ để đo kéo cầu |
| Promo2 | cửa hàng tham gia bán TB 6 559 so với 7 351, nhưng tham gia từ 2009-2015 theo lựa chọn: không so được |
| Giảm giá hoà vốn (margin giả định) | 25%: 9.3%; 30%: **12.0%**; 40%: 18.6%. Theo loại cửa hàng ở 30%: a 11.7%, b **7.1%**, c 12.1%, d 12.7% |

Headline mẫu: **"Khuyến mãi tăng 39% doanh số ngày thường, có lãi nếu mức giảm giá dưới khoảng 12% (giả định
margin 30%)"**. Chart mẫu: (1) bar lượt khách và giỏ theo thứ; (2) bar giảm giá hoà vốn theo loại cửa hàng với ba
mức margin; (3) line doanh số tuần xen kẽ, đánh dấu tuần khuyến mãi.

## Các quyết định cần cân nhắc

- **Mốc so sánh**: ngày thường của tuần không khuyến mãi là mốc tốt nhất có trong dữ liệu, nhưng không phải nhóm
  đối chứng: lịch đồng loạt toàn chuỗi, xen kẽ tuần. Nếu có kéo cầu (khách mua trữ), mốc bị kéo xuống và lift bị
  phóng đại; nếu khuyến mãi kéo khách mới quay lại tuần sau, lift bị đánh giá thấp. Dữ liệu không phân biệt được.
- **Lợi nhuận phải là giả định**: không có giá, mức giảm, giá vốn. Cách trung thực là đổi câu hỏi thành "mức giảm giá
  tối đa là bao nhiêu" và cho một bảng theo vài mức margin, rồi xin số thật từ tài chính.
- **Đề xuất phải kiểm được**: "cắt khuyến mãi thứ Năm, thứ Sáu" hay "dừng ở loại b" là giả thuyết; đề xuất tốt là
  thử nghiệm ngẫu nhiên theo cửa hàng (nửa giữ, nửa đổi), metric chính lợi nhuận gộp tuần, guardrail lượt khách,
  thời lượng đủ vài chu kỳ hai tuần (module 11 tính cỡ mẫu; DS module 04 có bài thiết kế thí nghiệm trên chính
  Rossmann).
- **Promo2**: không đưa ra kết luận nhân quả từ so sánh cửa hàng tham gia và không tham gia.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Đo tác động | 20 | Lift trên so sánh công bằng, tách lượt khách và giỏ; giải thích vì sao con số dashboard gần bằng (không kết luận nó đúng) |
| Nơi mạnh / yếu | 15 | Ít nhất hai chiều (thứ, loại cửa hàng / danh mục) có số; chỉ ra loại b / danh mục b và cuối tuần |
| Kéo cầu và mốc so sánh | 15 | Nêu được vấn đề lịch xen kẽ, có số cuối tuần hoặc theo tuần, nói rõ dữ liệu không đủ để đo |
| Điều kiện có lãi | 20 | Công thức hoặc bảng giảm giá hoà vốn theo vài mức margin, ghi rõ giả định, nhận ra loại b sát ngưỡng |
| Đề xuất | 20 | Hành động cụ thể, có thử nghiệm với nhóm đối chứng, metric và thời điểm xem lại |
| Giới hạn | 10 | Ít nhất hai giới hạn cụ thể (không có giá / giá vốn, không có đối chứng, Promo2 tự chọn) |

Từ 70 điểm trở lên là memo có thể gửi trước buổi họp ngân sách.

## Sai lầm hay gặp

- Báo "+39% doanh số" như tác động tăng thêm, không nói so với gì và không nói mốc có thể bị kéo xuống.
- Đổi lift ra "lợi nhuận tăng 39%" mà quên tiền giảm giá.
- Kết luận Promo2 làm giảm doanh số vì cửa hàng tham gia bán ít hơn.
- Đề xuất dồn khuyến mãi vào thứ Hai vì lift cao nhất, mà không xét lift giảm dần trong tuần có thể là khách mua
  trữ ngay đầu đợt (kéo cầu từ các ngày sau), không phải thứ Hai "hợp" khuyến mãi hơn.
