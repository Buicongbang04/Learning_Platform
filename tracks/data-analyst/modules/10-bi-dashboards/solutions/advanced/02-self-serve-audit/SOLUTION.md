# Hướng làm: audit kho question Metabase self-serve

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết ba hàm, kết quả trên fixture (ví dụ giả định),
khung memo, các quyết định cần cân nhắc và rubric chấm.

## Ba hàm

- **`normalize_name`**: `re.sub(r"[^\w\s]", " ", name.lower())` rồi `" ".join(s.split())`. `\w` của Python hiểu
  Unicode nên giữ "tháng", bỏ `·`, `:`, ngoặc. Thay dấu câu bằng khoảng trắng (không xoá thẳng) để
  "Doanh thu:theo tháng" không thành "doanh thutheo tháng".
- **`find_issues`**: bỏ card `archived`; gom `{tên chuẩn hoá: [id...]}` trước; rồi với mỗi card:
  - nhóm có hơn một id → `duplicate_name`, `detail` liệt kê id còn lại;
  - `dataset_query.type == "native"` và SQL khớp `quantity\s*\*\s*price|price\s*\*\s*quantity` (IGNORECASE) →
    `custom_revenue`;
  - `(collection or {}).get("authority_level") == "official"` và `not (description or "").strip()` →
    `no_description`;
  - `last_used_at or created_at` cũ hơn `now - timedelta(days=stale_days)` → `stale` (đọc bằng
    `datetime.fromisoformat(s.replace("Z", "+00:00"))`).

  Sắp theo `(card_id, issue)`.
- **`summarize`**: đếm theo `issue`, `dict(sorted(...))`.

Code phải chịu được card thật: question MBQL không có khoá `native`, card ở root có `collection` là `None` (hoặc
không có khoá), `description` `None`.

## Kết quả trên fixture (`now` = 30/10/2026)

| Card | Tên | Lỗi |
| --- | --- | --- |
| 1 | Doanh thu theo tháng (official) | `duplicate_name` |
| 2 | doanh thu  theo tháng (cá nhân, 37 lượt xem) | `duplicate_name`, `custom_revenue` |
| 4 | Revenue by country (official, MBQL) | `no_description` |
| 5 | Top khách 2010 | `custom_revenue`, `stale` (dùng lần cuối 02/05/2026) |
| 6 | Funnel thử | `stale` (chưa dùng, tạo 01/03/2026) |
| 8 | Doanh Thu Theo Tháng (team Sales) | `duplicate_name` |
| 9 | AOV theo tuần | `custom_revenue` (`Quantity*Price`) |
| 10 | Khách hoạt động (official, mô tả chỉ có khoảng trắng) | `no_description` |

Tổng hợp `{"custom_revenue": 3, "duplicate_name": 3, "no_description": 2, "stale": 2}`. Card 3 cùng tên và tự tính
doanh thu nhưng đã archive nên không tính; card 7 mới tạo, chưa dùng, chưa quá 90 ngày. Với `stale_days=30`, thêm
card 8 (dùng lần cuối 20/09) và 10 (02/08).

Trên Metabase của môi trường học (chỉ có bộ question ví dụ của Metabase và question bạn tạo ở các bài trước),
audit thường không ra lỗi nào: đó cũng là một kết quả, và memo nên nói rõ dữ liệu audit đến từ đâu.

## Khung memo

- **Phát hiện** (theo rủi ro, không theo thứ tự hàm): ba card "doanh thu theo tháng" cùng tồn tại, card 2 tự
  tính `quantity * price` (hôm nay ra cùng số vì bảng đã làm sạch, nhưng khi định nghĩa doanh thu đổi, ví dụ trừ
  phí ship hoặc chuyển sang doanh thu ròng, card này sẽ lệch mà không ai biết), và card đó có 37 lượt xem tức đang
  được dùng trong họp; hai card trong collection official không có mô tả, người xem không biết
  định nghĩa; hai card bỏ hoang làm kết quả tìm kiếm nhiễu.
- **Đề xuất**: một model "Doanh thu" (bảng `da.online_retail_ii` đã làm sạch, cột `revenue`) là điểm bắt đầu của
  mọi question doanh thu; collection official chỉ DA được đưa card vào, mỗi card có mô tả (định nghĩa, nguồn,
  owner); quy ước tên `[Miền] Metric theo chiều` (ví dụ `Sales · Doanh thu theo tháng`); card trùng: giữ card
  official, báo người tạo card trùng, chuyển họ sang card chính thức rồi archive (không xoá); card không dùng 90
  ngày: thông báo 2 tuần rồi archive. Bản trả phí có "verified question" và phân quyền collection chi tiết hơn; bản
  mở dùng quy ước collection + quyền.
- **Kế hoạch 30 ngày**: tuần 1 dựng model và mô tả card official (DA); tuần 2 gặp người dùng card trùng có lượt
  xem cao (card 2), chuyển họ sang card chính thức; tuần 3 archive card trùng và bỏ hoang sau thông báo; tuần 4
  chạy lại audit, báo chỉ số. Đo thành công: số card `custom_revenue` về 0, tỉ lệ lượt xem rơi vào collection
  official (ví dụ từ dưới 50% lên trên 80%), số câu hỏi "số nào đúng" trên Slack.

## Các quyết định cần cân nhắc

- **Không cấm self-serve**: người dùng tạo card trùng vì card chính thức thiếu thứ họ cần (chiều kênh, định dạng).
  Hỏi trước khi archive; đôi khi card trùng nên trở thành bản chính thức mới.
- **Archive, không xoá**: archive giữ lịch sử và khôi phục được; xoá làm hỏng dashboard đang trỏ tới card.
- **Phát hiện tự tính doanh thu bằng regex có giới hạn**: bỏ sót `SUM(qty*unit_price)` ở bảng khác tên cột, bắt
  nhầm khi `quantity * price` dùng cho mục đích khác. Đủ cho một lần audit; về lâu dài, metric định nghĩa ở model
  hoặc semantic layer (module 09) nên ít người phải viết lại công thức.
- **Ngưỡng bỏ hoang**: 90 ngày hợp với báo cáo tháng/quý; báo cáo năm (card 5 "Top khách 2010") có thể chỉ được mở
  mỗi năm một lần. Memo nên nêu ngoại lệ.
- **Đo trước và sau**: audit là script, chạy lại hằng tháng; chỉ số trong kế hoạch phải đo được từ API hoặc log.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Ba hàm | 25 | Test pass trên fixture; chạy được trên Metabase thật (MBQL, card không collection) |
| Phát hiện | 20 | Mỗi loại lỗi có số lượng, ví dụ cụ thể và rủi ro cho người ra quyết định; ưu tiên theo mức ảnh hưởng (lượt xem, collection) |
| Đề xuất | 25 | Có nguồn chuẩn (model/bảng sạch/semantic layer), quy tắc collection official và quyền, quy ước tên và mô tả, quy trình archive có báo trước; nêu giới hạn của bản Metabase đang dùng |
| Kế hoạch 30 ngày | 20 | 3-5 việc có thứ tự, người làm, chỉ số đo thành công đo được |
| Văn phong | 10 | Viết cho Head of Data: kết luận trước, ngắn (300-700 từ), không đổ lỗi người dùng |

Từ 70 điểm trở lên là đạt.

## Sai lầm hay gặp

- So tên chính xác từng ký tự: bỏ sót "doanh thu  theo tháng" và "Doanh Thu Theo Tháng".
- Tính card đã archive vào tên trùng.
- Code lỗi `KeyError` / `TypeError` trên card MBQL hoặc card ở root khi chạy trên Metabase thật.
- Memo đề xuất "xoá hết card trùng" mà không hỏi người đang dùng.
