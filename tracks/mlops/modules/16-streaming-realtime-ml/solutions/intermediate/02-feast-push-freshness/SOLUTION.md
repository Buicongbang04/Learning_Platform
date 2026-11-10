# Lời giải: Feast push, không skew, freshness

`features.py`, `push_job.py`, `freshness.py` cạnh tệp này là lời giải chạy được.

## Chọn online store

Bài dùng **SQLite** (tệp trong repo tạm) thay cho Redis của profile `feast` ở module 06: cả repo nằm trong thư mục mount vào container
Feast, không cần bật thêm dịch vụ, không có trạng thái dùng chung giữa các lần chạy hay giữa nhiều người chạy song song, và dọn dẹp chỉ là
xoá thư mục tạm. Cái giá: SQLite ghi đè theo thứ tự ghi, không so `event_timestamp` như Redis online store (Redis đọc `_ts` cũ trước khi
ghi và bỏ dòng cũ hơn, trừ khi bật `skip_dedup`). Bài biến nhược điểm đó thành bài học: tự bảo vệ quy tắc "không đè bằng giá trị cũ".

## Ý chính

- **`event_timestamp = window_end`.** Giá trị cửa sổ chỉ biết đủ khi cửa sổ đóng. Đặt `window_start` thì dòng huấn luyện point-in-time
  tại 08:16 thấy tổng của 08:15–08:30, tức thấy tương lai; model học trên đó rồi lên serving (nơi cửa sổ hiện tại chưa đóng) là
  skew kinh điển. Test hỏi offline tại `window_end + 60 s` để bắt đúng lỗi này.
- **Offline nhận mọi dòng, online chỉ dòng mới nhất mỗi zone và không cũ hơn hiện có.** Batch gửi lại cửa sổ cũ (late firing, replay,
  backfill) xảy ra thường xuyên; không có quy tắc này feature online "đi lùi". Guard trong lời giải là đọc rồi mới ghi, **không
  atomic**: hai writer cùng ghi một zone vẫn có thể đè nhau. Production cần một writer cho mỗi key (một consumer mỗi partition, key
  theo zone) hoặc để store so sánh lúc ghi (như Redis online store của Feast, hoặc ghi có điều kiện).
- **Kiểu dữ liệu là một phần của hợp đồng.** `float32` ở một phía là đủ để online và offline lệch ở chữ số thứ 8; test so `1e-9`.
- **Freshness = lúc đọc được trong online store - event time.** Trên máy kiểm, cửa sổ 2 giây + lateness 1 giây cho p50 khoảng 2.1 s và
  p95 khoảng 2.9 s, trong khi "nhận tới push" chỉ khoảng 0.8 s ở p95: đo từ lúc nhận làm dashboard đẹp gần gấp bốn. Với cửa sổ 15 phút,
  freshness của feature cửa sổ tối thiểu là thời gian chờ cửa sổ đóng (trung bình nửa cửa sổ + lateness): đó là lý do pipeline cần
  sliding window hoặc phát kết quả sớm (early firing) khi SLO freshness chặt.

## Lỗi hay gặp

- Import `feast` ở đầu `push_job.py`: test trên máy không có Feast nên lỗi import.
- Push online cả frame chưa sắp: dòng cuối được ghi thắng, có thể là cửa sổ cũ.
- Đo freshness bằng `pushed_at - received_at`: bỏ qua thời gian sự kiện đi tới broker, thời gian chờ cửa sổ, và thời gian tới khi đọc được.
