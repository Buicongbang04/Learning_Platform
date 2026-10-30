# Hướng làm: điều tra "doanh thu tháng 12 giảm 58%"

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết ba hàm, chuỗi điều tra, các con số tham
chiếu trên bộ thật, các quyết định cần cân nhắc và rubric chấm memo.

## Ba hàm

- **`reversed_lines`**: lọc dòng mua hợp lệ có `Customer ID` và dòng huỷ (`C...`, `Quantity < 0`) có
  `Customer ID`; đổi `StockCode` sang `str` (xlsx trộn `int` và `str`); đổi dấu `Quantity` của dòng huỷ;
  `merge` theo `Customer ID`, `StockCode`, `Quantity`; giữ cặp có giờ mua `<=` giờ huỷ; sắp theo
  `["InvoiceDate", "row"]` rồi `groupby("cancel_row").tail(1)` để mỗi dòng huỷ lấy dòng mua muộn nhất.
  Trả `pd.Series(tx.index.isin(hit), index=tx.index, name="reversed")`.
- **`customer_type`**: ngày mua đầu = `min(InvoiceDate)` theo khách trên `clean(history)` và `clean(tx)`
  gộp lại (hai sheet trùng 01-09/12/2010 không sao, vì chỉ lấy `min`); so `to_period("M")` của ngày đầu
  với của từng dòng; khách trống là `guest`.
- **`revenue_bridge`**: lọc `[start, end)` cho từng kỳ, `groupby(by).revenue.sum()`, `pd.concat(axis=1)`
  rồi `fillna(0)`, `diff`, `share_of_diff = diff / diff.sum()`, sắp theo `diff.abs()` giảm dần.

## Chuỗi điều tra và con số tham chiếu

| Bước | Con số (sheet `Year 2010-2011`, doanh thu gộp theo `clean`) |
| --- | --- |
| Chart dashboard | 11/2011: 1 509 496 GBP; 12/2011: 638 811 GBP; MoM **−57.7%** |
| Độ phủ | 11/2011 có 26 ngày giao dịch, 12/2011 có **8** (1-9/12, không có thứ Bảy 3/12); giao dịch cuối **09/12/2011 12:50**, nên ngày cuối cũng dở dang |
| Cùng số ngày, gộp | 1-9/12/2011: 638 811; 1-9/11/2011: 454 238 (**+40.6%**); 1-9/12/2010: 438 853 (**+45.6%**) |
| Ngoại lệ | Hoá đơn **581483** (khách 16446, UK, 09/12 9:15): 80 995 cái mã 23843 × 2.08 = **168 470 GBP**, bị huỷ bằng **C581484** lúc 9:27. Riêng nó là 26% doanh thu gộp 1-9/12/2011, gấp 15 lần hoá đơn lớn thứ hai (10 902) |
| Phần đã bị huỷ | 1-9/12/2011: 169 357; 1-9/11/2011: 5 413; 1-9/12/2010: 1 983. Cả năm 2 860 dòng mua bị huỷ |
| Cùng số ngày, đã bỏ phần bị huỷ | 1-9/12/2011: **469 453**; 1-9/12/2010: 436 870 (**+7.5%**); 1-9/11/2011: 448 825 (+4.6%) |
| Cầu theo quốc gia (YoY, +32 583) | UK **+20 318** (62%); Netherlands **+11 535** (35%, gần như một khách sỉ 14646: 11 728 so với 193); Japan −4 114 (không mua 1-9/12/2011) |
| Cầu theo loại khách (YoY) | returning +28 163; new +10 795 (46 → 27 khách mới nhưng chi nhiều hơn); guest −6 375 |
| Cầu theo loại khách (so 1-9/11) | guest +22 505, new −2 712, returning +835: so với tháng trước, khách quen đi ngang |
| Khách, hoá đơn | 573 → 611 khách có mã; 832 → 814 hoá đơn; giá trị hoá đơn TB 525 → 577 GBP, trung vị 263 → 301 |
| Sản phẩm (YoY) | 3 208 mã hàng hoá: 1 547 tăng, 1 647 giảm; 10 mã tăng nhiều nhất +38 044, 10 mã giảm nhiều nhất −39 646: thay đổi lan rộng, không do một sản phẩm. Các mã phí (`AMAZONFEE` −13 541, `DOT` +7 069, ...) cộng lại −6 304 |

**Câu chuyện đúng**: doanh thu không giảm. Cú rơi 58% là do so 8 ngày (ngày cuối dở dang) với 26 ngày. So
cùng 9 ngày, con số gộp "+46% so với năm trước" cũng sai, vì một đơn 168 nghìn GBP bị huỷ sau 12 phút vẫn
nằm trong doanh thu gộp. Bỏ phần đã bị huỷ, đầu tháng 12/2011 cao hơn cùng kỳ năm trước khoảng **7.5%**,
tăng chủ yếu từ khách quen ở UK và một khách sỉ Hà Lan.

Headline mẫu: **"Doanh thu 1-9/12 cao hơn cùng kỳ 7.5%; con số giảm 58% là do tháng 12 mới có 8 ngày"**.
Ba chart mẫu: (1) line doanh thu cộng dồn ngày 1-9 của ba kỳ, kỳ 12/2011 vẽ cả bản gộp (nét đứt) và bản đã
bỏ đơn huỷ, chú thích hoá đơn 581483; (2) bar ngang doanh thu mỗi ngày tháng 11-12/2011 hoặc bảng độ phủ,
chú thích "dữ liệu tới 12:50 ngày 9/12"; (3) bar ngang cầu doanh thu YoY theo quốc gia hoặc loại khách,
sắp theo `diff`, màu tăng/giảm khác nhau.

## Các quyết định cần cân nhắc

- **So với kỳ nào**: 1-9/11 không trừ mùa vụ (đầu tháng 12 là cao điểm đặt quà); 1-9/12 năm trước trừ
  được mùa vụ nhưng ngày trong tuần lệch (1/12/2010 là thứ Tư, 1/12/2011 là thứ Năm). Cả hai kỳ đều có 8
  ngày giao dịch, nên chấp nhận được; nói rõ trong Giới hạn.
- **Doanh thu gộp hay ròng**: dashboard dùng gộp (bỏ hoá đơn huỷ nhưng giữ đơn gốc). Bỏ đơn đã bị huỷ là
  cách đo đúng hơn cho câu hỏi "khách đã thật sự mua bao nhiêu". Quy tắc ghép của `reversed_lines` không
  bắt được huỷ một phần, huỷ của khách vãng lai, hay hai lần huỷ cùng ghép một dòng mua: nói rõ đây là ước
  lượng. Cách thay thế: cộng thẳng dòng huỷ (âm) vào doanh thu, cho 1-9/12/2011 là 433 686 so với 377 488
  năm trước (+14.9%); kết luận "không giảm" giữ nguyên, độ lớn thì nhạy với định nghĩa.
- **Ngày cuối dở dang**: 9/12 dừng lúc 12:50; nếu so "8 ngày đủ" thì nên cân nhắc bỏ ngày 9 ở cả hai kỳ.
- **Khách mới**: lịch sử của tháng 12/2010 chỉ có một năm (sheet 2009-2010), của tháng 12/2011 có hai
  năm, nên "khách mới" năm sau khắt khe hơn. Khách vãng lai không có mã nên không biết mới hay cũ.
- **Mã phí không phải hàng hoá**: tách `POST`, `DOT`, `AMAZONFEE`, `M`, `BANK CHARGES`, ... khỏi phân tích
  sản phẩm, nếu không "AMAZONFEE" thành "sản phẩm giảm mạnh nhất".
- **Tập trung**: Netherlands +11.5 nghìn là một khách; một khách sỉ đổi lịch đặt hàng có thể đảo kết luận
  theo quốc gia. Báo số khách bên cạnh số tiền.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Xác nhận con số | 15 | Chỉ ra 8 so với 26 ngày và ngày cuối dở dang; không gọi cú rơi 58% là "giảm" |
| So sánh công bằng | 15 | So cùng số ngày với cả kỳ trước và cùng kỳ năm trước; giải thích vì sao cùng kỳ năm trước trừ được mùa vụ |
| Kiểm ngoại lệ | 15 | Tìm ra hoá đơn 581483 bị huỷ; báo con số trước và sau khi bỏ; nói định nghĩa doanh thu đang dùng |
| Tách thay đổi | 20 | Cầu doanh thu theo ít nhất hai chiều (quốc gia, loại khách, sản phẩm); nêu được thay đổi tập trung hay lan rộng, có số khách bên cạnh số tiền; bỏ mã phí khỏi phân tích sản phẩm |
| Chart | 15 | Ba chart đúng loại, tiêu đề là kết luận có con số, kỳ dở dang và ngoại lệ có annotation |
| Memo | 15 | Headline trả lời thẳng câu hỏi; người đọc không cần biết tên cột; việc cần làm có người làm và thời điểm xem lại (sửa dashboard để tháng chưa kết thúc hiện nét đứt và so cùng kỳ; cảnh báo đơn lớn bị huỷ; xem lại số khi đủ tháng 12) |
| Giới hạn | 5 | Nêu được ít nhất hai giới hạn cụ thể ở trên |

Từ 70 điểm trở lên là memo có thể gửi trước buổi họp HĐQT.

## Sai lầm hay gặp

- Dừng ở "tháng 12 mới có 8 ngày" và báo "+46% so với năm trước" mà không kiểm hoá đơn lớn.
- Ngoại suy "tháng 12 sẽ đạt X triệu" từ 8 ngày đầu, bỏ qua việc khách sỉ đặt hàng Giáng sinh sớm.
- Tách theo phân khúc trên con số gộp còn chứa đơn đã bị huỷ: UK "đóng góp" 94% thay đổi, sai câu chuyện.
- Memo mở bằng quá trình làm ("Tôi đã đọc hai sheet...") thay vì kết luận.
