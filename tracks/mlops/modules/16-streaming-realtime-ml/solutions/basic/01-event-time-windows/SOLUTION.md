# Lời giải: cửa sổ theo event time, watermark, trễ và trùng

`windows.py` cạnh tệp này là lời giải chạy được; đáp án quiz ở `quiz-answers.yaml`.

## Ý chính

- **Cửa sổ gán theo event time.** `tumbling_start = ts - ts % size`. Sliding là mọi `start` bội của `step` trong `(ts - size, ts]`;
  session mở `[ts, ts + gap)` cho từng sự kiện rồi gộp khoảng gối nhau.
- **Watermark là lời hứa "sự kiện cũ hơn mức này coi như đã đến hết".** Ở đây là heuristic bounded out-of-orderness:
  `max(event time đã thấy) - lateness`. Cửa sổ đóng khi `window_end <= watermark`; sự kiện đến sau khi cửa sổ của nó đã đóng là trễ.
- **`lateness` là núm vặn giữa đúng và nhanh.** Lớn thì ít bỏ sự kiện nhưng feature có muộn đúng bằng chừng đó; nhỏ thì nhanh nhưng
  bỏ nhiều. Chọn bằng phân phối độ trễ thật (p99 của `received - event_time`), không đoán.
- **Chống trùng trước, rồi mới xét trễ.** Bản gửi lại của một sự kiện trễ phải được đếm là trùng; đếm nhầm thành trễ làm bạn đi chỉnh
  lateness trong khi vấn đề là producer retry.
- **Trạng thái chống trùng phải có hạn.** Lời giải giữ `set` mọi `event_id` cho đơn giản; production giữ theo cửa sổ thời gian (vài lần
  lateness) hoặc dùng exactly-once của engine.

## Đáp án quiz (giải thích)

- `event-vs-processing` b: theo processing time, sự kiện của 20 phút chết dồn vào cửa sổ lúc đọc lại.
- `lateness-tradeoff` a: đánh đổi độ đầy đủ lấy độ trễ.
- `window-kind` c: "10 phút gần nhất, cập nhật mỗi phút" là sliding.
- `duplicates` a, b: chống trùng ở consumer theo `event_id`, hoặc chặn bản sao từ đầu bằng producer idempotent. Upsert (c) chỉ làm
  việc ghi lại cùng một kết quả không cộng dồn; bản sao đã được đếm trong `trips` trước khi ghi. Tăng partition (d) không liên quan.
- `watermark-source` a: một sự kiện tương lai kéo watermark lên và làm mọi sự kiện sau thành trễ (đúng sự cố ở Intermediate 03).
- `engine-choice` b: đội nhỏ, Python, tải vừa: chọn thứ vận hành được; Flink khi cần quy mô, state lớn và độ trễ thấp.
- `flink-vs-spark` a: micro-batch của Spark.
- `freshness-measure` b.

## Lỗi hay gặp

- Cập nhật watermark trước khi xét trễ: sự kiện làm watermark nhảy có thể tự coi mình là trễ.
- So `window_end < watermark` thay vì `<=`: cửa sổ đóng trễ một nhịp, test thời điểm đóng bắt được.
- Không sắp thứ tự khi đóng nhiều cửa sổ cùng lúc: downstream ghi online store theo thứ tự đó, sai thứ tự là đè giá trị mới bằng cũ.
