# Hướng làm: funnel theo visitor và theo phiên

> `starter/run_query.py` là helper để chạy thử SQL trên dữ liệu thật, không được chấm và không có bản lời giải: giữ nguyên.

Bài Advanced không có một đáp án duy nhất ở phần memo. Hai truy vấn có kết quả xác định (test chấm); dưới đây là
cách viết, con số tham chiếu, các quyết định cần cân nhắc và rubric.

## Hai truy vấn

- **`visitor_funnel.sql`**: ba CTE nối tiếp `v(visitor_id, t_view)`, `c(visitor_id, t_cart)`, `p(visitor_id)`, mỗi
  CTE join `events` với điều kiện thời gian `>=` mốc của bước trước rồi lấy `min`. Đếm bằng `UNION ALL` ba dòng;
  `conv_from_prev = visitors / lag(visitors) OVER (ORDER BY step)`, `conv_from_first = visitors /
  first_value(visitors) OVER (ORDER BY step)`.
- **`session_funnel.sql`**: thêm hai CTE ở đầu: `flagged` (cờ phiên mới bằng `lag`), `sessions` (tổng luỹ kế của
  cờ, frame `ROWS`); ba CTE bước giống trên nhưng khoá là `(visitor_id, session_no)`. Sự kiện cùng mốc thời gian
  có khoảng cách 0 nên luôn cùng phiên, kết quả không phụ thuộc thứ tự giữa chúng.

Cả hai chạy dưới một giây trên 2.76 triệu sự kiện bằng DuckDB.

## Con số tham chiếu

| Cách đếm | View | Thêm giỏ | Mua | Xem → giỏ | Giỏ → mua | Xem → mua |
| --- | --- | --- | --- | --- | --- | --- |
| Visitor, có thứ tự | 1 404 179 | 32 934 | 9 952 | 2.35% | 30.2% | 0.71% |
| Phiên 30 phút, có thứ tự | 1 755 781 | 36 677 | 10 722 | 2.09% | 29.2% | 0.61% |
| Visitor, không thứ tự (`count(DISTINCT)` theo event) | 1 404 179 | 37 722 | 11 719 | 2.69% | 31.1% | 0.83% |

- 2 129 visitor có lần thêm giỏ đầu tiên **trước** lần xem đầu tiên (xem trước khi bắt đầu kỳ dữ liệu, hoặc thêm
  giỏ từ trang danh sách); 428 visitor mua mà không có `view` nào.
- Với 9 952 visitor đi hết funnel: trung vị từ lần xem đầu tới lần mua là **24 phút**, nhưng 10% mất hơn **9 ngày**
  (220 giờ): funnel theo phiên bỏ sót nhóm "xem hôm nay, mua tuần sau".

## Các quyết định cần cân nhắc

1. **Có thứ tự hay không**: funnel không thứ tự thổi phồng giỏ 15% và người mua 18%. Có thứ tự là đúng nghĩa
   "đi qua funnel"; nhưng phải nói rõ cửa sổ dữ liệu cắt hai đầu làm mất "lần xem trước 03/05".
2. **Theo visitor hay theo phiên**: theo visitor trả lời "bao nhiêu người cuối cùng mua" (mục tiêu kinh doanh); theo
   phiên trả lời "một lượt ghé có dẫn tới mua không" (đo thay đổi giao diện, A/B test). Hai con số khác nhau và
   đều đúng; memo phải chọn một làm metric chính và giải thích cái còn lại.
3. **Ngưỡng 30 phút**: quy ước phổ biến (Google Analytics dùng 30 phút), không phải chân lý. Thử 15 và 60 phút để
   xem kết luận có đổi không.
4. **Không xét mặt hàng**: xem A rồi mua B vẫn tính. Funnel theo mặt hàng (`visitor_id, item_id`) khắt khe hơn
   và trả lời câu hỏi khác (trang sản phẩm nào chuyển đổi tốt).
5. **Bước nào ưu tiên**: xem → giỏ rơi 1.37 triệu visitor, giỏ → mua rơi 22 982. Cải thiện tương đối 10% ở bước
   đầu thêm khoảng 3 300 giỏ (khoảng 1 000 đơn nếu tỉ lệ sau giữ nguyên); 10% ở giỏ → mua thêm khoảng 1 000 đơn. Hai
   con số gần bằng nhau, nên lập luận phải dựa thêm vào **chi phí và khả năng tác động** (sửa checkout thường rẻ
   hơn, nhưng traffic xem có thể chứa nhiều bot và người chỉ lướt), không chỉ "bước rơi nhiều nhất". Memo tốt nêu
   được đánh đổi này và đề xuất thí nghiệm để kiểm.
6. **Bot và traffic lạ**: 1.4 triệu visitor, phần lớn chỉ một lượt xem. Không có cột thiết bị/nguồn nên không lọc
   được bot; ghi vào giới hạn.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Định nghĩa | 15 | Nêu rõ thứ tự bước, đơn vị đếm (visitor/phiên), ngưỡng phiên, kỳ dữ liệu cắt hai đầu |
| Số liệu | 20 | Đủ hai funnel, tỉ lệ so bước trước và bước đầu; giải thích vì sao hai funnel khác nhau |
| Không thứ tự vs có thứ tự | 10 | Chỉ ra đếm `DISTINCT` theo event thổi phồng bao nhiêu và vì sao |
| Khuyến nghị | 25 | Chọn bước ưu tiên có lập luận định lượng (quy mô và tác động), nêu đánh đổi, có giả thuyết kiểm được bằng A/B |
| Memo | 20 | Headline là kết luận có số; PM không cần biết SQL; việc cần làm có người làm và mốc xem lại |
| Giới hạn | 10 | Ít nhất hai giới hạn cụ thể (bot, không có nguồn traffic, cửa sổ dữ liệu, không xét mặt hàng, mua sau nhiều ngày) |

Từ 70 điểm trở lên là memo gửi được.

## Sai lầm hay gặp

- `count(DISTINCT visitor_id)` theo từng `event` rồi gọi là funnel: bước sau có thể chứa người chưa qua bước trước.
- Chia phiên bằng `date_trunc('hour', ...)` hay theo ngày: phiên qua nửa đêm bị cắt đôi.
- Frame mặc định `RANGE` khi tính tổng luỹ kế cờ phiên với `ORDER BY event_time`: sự kiện trùng mốc nhận cùng giá
  trị, may là ở đây vô hại; vẫn nên ghi `ROWS`.
- Báo "tỉ lệ chuyển đổi 0.71%" không kèm định nghĩa: người nghe so với "2-3% của ngành" (thường tính theo phiên).
