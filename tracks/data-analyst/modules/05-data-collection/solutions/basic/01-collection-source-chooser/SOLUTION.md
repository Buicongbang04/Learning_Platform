# Lời giải: chọn nguồn và cách thu thập

## Cách làm

Mỗi câu trả lời bốn câu hỏi ở phần 1 lý thuyết:

1. Dữ liệu dùng cho quyết định gì, cần chính xác tới đâu, một lần hay lặp lại?
2. Ai sở hữu nguồn, có cách lấy chính thức (bảng warehouse, API, export) không?
3. Lấy dữ liệu có ảnh hưởng tới hệ thống nguồn không (tải, rate limit)?
4. Có được phép không (ToS, dữ liệu cá nhân, bản quyền), và giữ bí mật (key, mật khẩu) thế nào?

Phương án sai đều "lấy được dữ liệu"; chúng sai vì bỏ qua một trong bốn câu đó.

## Đáp án từng câu

| Câu | Đáp án | Câu hỏi quyết định |
| --- | --- | --- |
| `prod-db` | a. Tổng hợp trên read replica | 3: không đè tải lên production; đưa tính toán tới gần dữ liệu |
| `partner-file` | b. Tìm dòng bị mất | 1: số dùng cho quyết định phải khớp control total trước khi tính |
| `api-vs-scrape` | c. World Bank API, lưu JSON thô | 2: có nguồn chính thức, có giấy phép (CC BY 4.0), tái lập được |
| `robots-meaning` | d. Hỏi pháp chế | 4: `robots.txt` là quy ước kỹ thuật, ToS là thoả thuận |
| `personal-data` | a, b, c | 4: dữ liệu cá nhân, mục đích khác mục đích công bố, ToS |
| `api-key` | b. Biến môi trường / `.env` | 4: bí mật không bao giờ nằm trong code hay lịch sử git |
| `http-200-error` | c. Kiểm cả nội dung | 2: hiểu cách API báo lỗi |
| `pagination` | d. 50 bản ghi, thiếu âm thầm | 2: đọc metadata phân trang, đối chiếu `total` |
| `daily-pipeline` | d. Idempotent, log, bàn giao | 1: việc lặp lại cần chạy lại an toàn và có người bảo trì |
| `raw-first` | a. Parse lại không cần gọi lại | 1, 3: tái lập, ít tải cho nguồn, truy vết được |

## Giải thích thêm

- **prod-db**: `SELECT *` trên production vừa nặng cho hệ thống phục vụ khách hàng, vừa kéo về hàng triệu dòng chỉ
  để tổng thành 90 con số. Read replica trễ vài giây không ảnh hưởng một báo cáo 90 ngày. Export Excel hằng ngày (c)
  tạo ra bản sao không ai kiểm; scrape trang quản trị (d) là cách lấy dữ liệu nội bộ tệ nhất.
- **partner-file**: chênh 38 dòng có thể là 38 đơn lớn. Lỗi hay gặp: mô tả có xuống hàng trong ô có dấu ngoặc kép
  bị đọc sai, ký tự lạ làm parser bỏ dòng, dòng tổng bị tính như dữ liệu. Nhân bù (c) là bịa số.
- **api-vs-scrape**: World Bank có API miễn phí, không cần key, có `lastupdated` trong metadata để ghi phiên bản.
  Wikipedia (a) lấy lại từ nguồn khác, định dạng đổi thường xuyên; LLM (d) có thể bịa số.
- **robots-meaning**: `robots.txt` nói website *muốn* bot làm gì; điều khoản sử dụng là thoả thuận có thể ràng buộc
  về pháp lý. Nghỉ giữa request (b) là lịch sự, không thay được sự cho phép; proxy để tránh bị phát hiện (c) là dấu hiệu
  bạn biết mình không được phép.
- **personal-data**: (d) đúng về tốc độ nhưng không phải vấn đề; mua danh sách cũng không làm việc gọi chào hàng hợp
  pháp nếu người trong danh sách không đồng ý.
- **api-key**: xoá output (a) không xoá key trong source; base64 (c) không phải mã hoá; key lọt vào git thì phải
  thu hồi và cấp key mới, vì lịch sử commit giữ nó mãi.
- **http-200-error**: World Bank trả lỗi tham số trong body với HTTP 200; code chỉ kiểm status sẽ lấy `body[1]`, gặp
  `IndexError` hoặc trả bảng rỗng. Client tốt kiểm cả cấu trúc body và báo lỗi rõ.
- **pagination**: thiếu trang không gây lỗi. Luôn lặp theo `pages` (hoặc `next`/cursor) và so số bản ghi nhận được
  với `total`.
- **daily-pipeline**: idempotent nghĩa là chạy lại cùng ngày cho cùng kết quả (xoá-rồi-ghi theo ngày, hoặc upsert theo
  khoá). Xoá cả bảng nạp lại (c) tốn và nguy hiểm khi lỗi giữa chừng. Khi nhiều dashboard phụ thuộc, nó là pipeline,
  nên có lịch, log, cảnh báo và người sở hữu (thường là DE).
- **raw-first**: lớp raw là bản ghi bất biến của "nguồn trả gì, lúc nào". Sửa parser thì parse lại từ raw; nguồn sửa số
  (World Bank, Open-Meteo đều sửa) thì so được bản cũ với bản mới.
