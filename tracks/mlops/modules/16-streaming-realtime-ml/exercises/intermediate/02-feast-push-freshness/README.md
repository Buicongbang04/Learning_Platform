---
title: Feast push feature cửa sổ vào online store, không skew, đo freshness p50/p95
level: intermediate
services: []
files:
  - path: starter/features.py
    note: 4 TODO (định nghĩa Feast)
  - path: starter/push_job.py
    note: 2 TODO
  - path: starter/freshness.py
    note: 1 TODO
  - path: tests/test_push.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py nyc-tlc
  - uv run pytest tracks/mlops/modules/16-streaming-realtime-ml/exercises/intermediate/02-feast-push-freshness -q
---

## Mục tiêu

Nối đầu ra của consumer cửa sổ vào Feast bằng **push source**: feature vừa tính xong được ghi thẳng vào online store (cho serving)
và offline store (cho huấn luyện), không đợi job materialize. Ba thứ phải đúng: giá trị online khớp tính batch trên cùng dữ liệu,
dòng huấn luyện lấy theo point-in-time không nhìn thấy tương lai, và một lần gửi lại cửa sổ cũ không đè giá trị mới hơn. Cuối cùng
bạn đo freshness theo đúng định nghĩa: từ event time tới lúc giá trị đọc được trong online store.

## Đề bài

Feast chỉ chạy trong container (`mlopskit.feast_run`/`feast_python`, image `mlops-feast:0.67.0` build lần đầu). Test dựng một feature
repo tạm với `feature_store.yaml` dùng **SQLite** làm online store (tệp `data/online.db` trong repo, không cần dịch vụ nào) và file
offline store, tạo sẵn `data/zone_window.parquet` rỗng (cột `zone_id`, `trips`, `avg_fare`, `event_timestamp`), chép
`features.py` và `push_job.py` của bạn vào rồi chạy `feast apply`.

1. `starter/features.py`: entity `zone` (join key `zone_id`, `ValueType.INT64`); `FileSource` trỏ `data/zone_window.parquet`
   (`timestamp_field="event_timestamp"`); `PushSource` tên `zone_window_push` dùng FileSource đó làm `batch_source`; `FeatureView`
   tên `zone_window` với hai feature `trips` (`Int64`) và `avg_fare` (`Float64`), `source` là push source, `ttl` từ 1 đến 24 giờ.
2. `starter/push_job.py` (được import cả trên máy, nơi không có Feast, nên chỉ import `feast` bên trong `push`):
   - `to_push_frame(windows)`: nhận list dòng cửa sổ như đầu ra bài Intermediate 01 (`zone_id`, `window_start`, `window_end`,
     `trips`, `avg_fare`, thời điểm là giây epoch) và trả `DataFrame` đúng bốn cột theo thứ tự `zone_id` (int64), `trips` (int64),
     `avg_fare` (float64), `event_timestamp` (datetime UTC), sắp tăng dần theo `event_timestamp`. **Một cửa sổ chỉ biết đủ giá trị
     khi nó đóng**: `event_timestamp` là thời điểm **sớm nhất** mà giá trị cửa sổ đã đủ, để dòng huấn luyện lấy point-in-time tại
     một thời điểm bất kỳ chỉ thấy cửa sổ đã đóng trước thời điểm đó (test so đúng giá trị này).
   - `push(store, frame) -> int`: ghi **mọi** dòng vào offline store qua push source; với online store, chỉ ghi dòng có
     `event_timestamp` lớn nhất của mỗi zone, và chỉ khi nó **không cũ hơn** giá trị online hiện có của zone đó. Trả số dòng đã
     ghi online. Lưu ý: online store SQLite của Feast ghi đè theo thứ tự ghi, **không** so `event_timestamp`; đọc timestamp hiện có
     bằng `get_online_features(...).to_dict(include_event_timestamps=True)` (khoá `trips__ts`, giây epoch, 0 khi chưa có).
3. `starter/freshness.py`: `freshness(records)` với mỗi record có `event_time`, `received_at`, `pushed_at`, `visible_at` (giây epoch)
   trả `{"n", "p50", "p95"}` (giây, percentile kiểu mặc định của `numpy.percentile`); list rỗng thì `n = 0`, hai số kia `None`.

Test kiểm:

- Chuyến taxi thật (3 zone, 2 giờ, dời mốc thời gian về gần hiện tại) được gộp **bằng pandas** thành cửa sổ 15 phút; các cửa sổ đi
  vào `push` theo 3 micro-batch xáo thứ tự bên trong, rồi một batch thứ tư gửi lại 10 cửa sổ cũ. Online của mỗi zone phải là cửa
  sổ mới nhất, giá trị khớp batch tới sai số tương đối `1e-9`; số dòng ghi online là 3 cho mỗi micro-batch đầu và 0 cho batch gửi
  lại; zone không tồn tại trả `None`.
- `get_historical_features` tại `window_end + 60 giây` của mỗi cửa sổ phải trả đúng giá trị cửa sổ đó.
- Freshness đo sống: test phát 150 chuyến (cửa sổ 2 giây, lateness 1 giây để chạy nhanh) qua `to_push_frame` và `push` của bạn, ghi
  lúc giá trị đọc được trong online store; `freshness` phải khớp percentile tính lại trong test và p95 không quá 10 giây (dư 2 lần
  so với ước tính cửa sổ + lateness + 2 giây đẩy và đọc).

## Tiêu chí đạt

- Test pass.
- Bạn chỉ ra được trên số đo của mình: freshness p50 lớn hơn nhiều so với "từ lúc nhận tới lúc push", phần lớn do chờ cửa sổ đóng,
  và nếu đo từ lúc consumer nhận sự kiện thì dashboard sẽ báo đẹp hơn thực tế bao nhiêu.
- Bạn giải thích được vì sao online store cần quy tắc "không ghi đè bằng giá trị cũ hơn", và vì sao Redis online store của Feast
  tự làm việc đó còn SQLite thì không (đọc mã `online_write_batch` của hai store).

## Gợi ý

### Gợi ý 1

`pd.to_datetime(series_int, unit="s", utc=True)` cho cột thời điểm UTC. Nếu đặt `event_timestamp` là `window_start`, dòng huấn
luyện tại 08:16 sẽ thấy tổng của cửa sổ 08:15–08:30, tức thấy 14 phút tương lai: đó là skew giữa train và serve.

### Gợi ý 2

Trong `push`: `store.push("zone_window_push", frame, to=PushMode.OFFLINE)` cho mọi dòng; `frame.groupby("zone_id").tail(1)` sau
khi sắp theo thời gian cho dòng mới nhất mỗi zone; so với `trips__ts` rồi `store.push(..., to=PushMode.ONLINE)` cho phần còn lại.
`float32` làm `avg_fare` lệch ở chữ số thứ 8: giữ `float64`.
