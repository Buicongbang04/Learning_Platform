# Lời giải: mô phỏng LLM gateway

## Cách làm

Một vòng qua trace đã sắp theo `t`, trạng thái giữ ngoài vòng: `cache` (khoá → (t lưu, user)), `fails_in_row`,
`open_until`, danh sách độ trễ, chi phí, bộ đếm. Với mỗi request:

1. Tính khoá (`(user, key)` hoặc `key`) và `cacheable` (TTL > 0 và không phải request cá nhân dưới scope `public`).
   Trúng cache thì ghi độ trễ cache, đếm rò rỉ nếu cá nhân và khác user, sang request kế.
2. Cascade: gọi small, `served = small_conf >= threshold`.
3. Chưa xong: nếu `t >= open_until` thì gọi large; thành công đặt `fails_in_row = 0`; lỗi thì cộng timeout, tăng
   `fails_in_row`, đạt `k` thì `open_until = t + cooldown`. Large lỗi hoặc bị breaker chặn thì gọi fallback nếu bật.
4. Được phục vụ thì ghi độ trễ và (nếu `cacheable`) ghi cache.

## Kết quả trên trace (giá giả định: small 0.10/0.40, large 2/10, fallback 0.30/2.50 USD mỗi triệu token)

| Cấu hình | Availability | Cache hit | Rò rỉ | USD / 1 000 | p50 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| Chỉ large | 0.837 | 0 | 0 | 5.156 | 2.47 s | 4.31 s |
| + fallback (timeout 10 s) | 1.000 | 0 | 0 | 5.343 | 2.70 s | 12.14 s |
| + fallback (timeout 3 s) | 1.000 | 0 | 0 | 5.343 | 2.70 s | 5.34 s |
| + breaker 3 lỗi / 60 s | 1.000 | 0 | 0 | 5.309 | 2.39 s | 4.48 s |
| + cache public 1 giờ | 1.000 | 0.478 | 0 | 2.882 | 1.29 s | 3.93 s |
| + cascade ngưỡng 0.7 | 1.000 | 0.478 | 0 | 2.412 | 0.38 s | 4.32 s |
| cache theo user (thay cho public) | 1.000 | 0.128 | 0 | 4.630 | 2.24 s | 4.32 s |
| cache global (thay cho public) | 1.000 | 0.942 | **925** | 0.301 | 0.01 s | 1.75 s |

Đọc bảng:

- **Fallback cứu availability nhưng timeout dài phá p95.** Trong 10 phút sự cố, mỗi request chờ đủ 10 s mới chuyển
  sang fallback: p95 lên 12.1 s. Giảm timeout xuống 3 s đưa p95 về 5.3 s; circuit breaker còn tốt hơn (4.5 s) vì sau 3
  lỗi liên tiếp nó ngừng chờ hẳn, và 305 lần gọi large vô ích được tránh. Timeout phải đặt theo phân phối độ trễ thật
  của model (ví dụ p99 cộng biên), không phải số tròn.
- **Cache là đòn bẩy chi phí lớn nhất, và nguy hiểm nhất.** Cache global trông tuyệt vời (rẻ hơn 17 lần so với không cache, p95 1.75 s) vì
  câu hỏi cá nhân có cùng văn bản giữa các khách, và cũng vì thế 925 lần một khách nhận thông tin đơn hàng của người
  khác. Cache theo user an toàn nhưng chỉ trúng 12.8%. Cache public (chỉ câu hỏi không cá nhân) giữ được phần lớn lợi
  ích, 0 rò rỉ. Ngoài đời, "cá nhân hay không" do router/classifier quyết định và có sai số: cần thêm kiểm tra ở tầng
  output (câu trả lời có PII không) trước khi ghi cache.
- **Cascade đổi chi phí lấy độ trễ đuôi và một rủi ro chưa đo.** p50 giảm mạnh (model nhỏ nhanh) nhưng p95 tăng nhẹ
  vì request bị chuyển lên large trả độ trễ của cả hai. Hạ ngưỡng xuống 0.5 rẻ thêm (1.47 USD/1 000) nhưng mô phỏng
  coi mọi câu trả lời của small là đúng: ngưỡng phải chọn bằng eval có nhãn (độ chính xác của small theo từng mức
  confidence), và confidence của LLM thường được hiệu chuẩn kém.
- Chi phí "+ fallback" cao hơn "chỉ large" vì 326 request trước đây thất bại giờ được phục vụ (và tính tiền).

## Bẫy thường gặp

- Ghi cache cả request thất bại; làm mới thời điểm lưu khi trúng (cache không bao giờ hết hạn với khoá phổ biến).
- Scope `public` chặn đọc nhưng quên chặn ghi câu hỏi cá nhân.
- Breaker đếm tổng số lỗi thay vì lỗi liên tiếp, hoặc vẫn cộng timeout khi đang ngắt.
- Tính percentile trên cả request thất bại (độ trễ của request không có câu trả lời không có nghĩa).
