# Lời giải: feature online đứng yên

`zone_stream.py` cạnh tệp này là lời giải chạy được. `make_fixtures.py` sinh lại `events.jsonl` và `expected.json` từ TLC 2019-03.

## Nguyên nhân gốc

Từ 08:50 tới 09:00 một gateway mới (canary) gửi một phần sự kiện với `pickup_at` dạng giờ địa phương có offset, ví dụ
`2019-03-05T15:50:07+07:00` (tức 08:50:07 UTC). Hàm `_when` cũ bỏ `Z` rồi `.replace(tzinfo=timezone.utc)`: với chuỗi có offset,
`replace` **ghi đè** offset thay vì đổi múi giờ, nên 15:50 bị hiểu là 15:50 UTC, tức đi trước 7 giờ.

Một sự kiện như vậy kéo `_progress` (watermark: `max event time - hold_s`) lên khoảng 15:47. Từ đó mọi sự kiện đúng giờ đều có
`window_end <= watermark` nên bị tính là đến trễ (`skipped`) và bỏ đi; cửa sổ 08:45–09:00 bị đóng ngay với dữ liệu mới có 5 phút, và không cửa sổ đúng giờ nào sau đó
nhận được sự kiện. Canary
rollback lúc 09:00 không cứu được: watermark chỉ tăng, nên feature đứng yên tới khi consumer khởi động lại (và mất
trạng thái). Không có lỗi nào được log vì
theo mã, đây là hành vi "đúng" với sự kiện trễ.

## Sửa

1. Parse đúng: `datetime.fromisoformat(raw).astimezone(timezone.utc)` (chuỗi không có offset thì coi là UTC theo hợp đồng).
2. Phòng vệ: sự kiện có event time muộn hơn thời điểm broker nhận quá 5 phút là hỏng, đếm `rejected` và bỏ, không để nó chạm watermark.
   Đây là chặn chung cho mọi nguồn "tương lai" (đồng hồ thiết bị sai, đơn vị mili giây, múi giờ), không chỉ lỗi lần này.

## Phát hiện sớm hơn

- Cảnh báo **độ trễ watermark**: `now - watermark` (hoặc `max received_at - watermark`) âm hoặc nhảy bất thường, và tỉ lệ `skipped`
  trên tổng vượt vài phần trăm trong 5 phút. Consumer lag không bắt được vì consumer vẫn đọc kịp.
- Cảnh báo freshness của feature online theo `event_timestamp` (đo từ phía đọc), không theo lúc ghi.
- Hợp đồng dữ liệu ở producer: `pickup_at` bắt buộc UTC dạng `Z`, schema registry hoặc kiểm tra ở gateway từ chối định dạng khác; canary
  của producer phải có kiểm tra tương thích với consumer.

## Postmortem ngắn (mẫu)

Tác động: feature `trips`/`avg_fare` của 3 zone đứng yên 09:00–10:05, model ETA dùng feature cũ tới 65 phút. Phát hiện: đội serving
nhìn thấy, không có cảnh báo. Nguyên nhân: canary gateway gửi timestamp có offset, consumer parse sai thành tương lai, watermark nhảy 7
giờ. Hành động: sửa parse, chặn event time tương lai, cảnh báo độ trễ watermark và tỉ lệ skipped, hợp đồng UTC ở gateway.
