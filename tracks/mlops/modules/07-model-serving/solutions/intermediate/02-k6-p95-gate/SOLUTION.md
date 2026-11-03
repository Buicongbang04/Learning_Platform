# Lời giải: cổng tải k6

## Cách làm

Hai scenario `constant-arrival-rate`: `warmup` (10/giây x 3 giây) rồi `measure` (30/giây x 8 giây, `startTime: "4s"`). Ngưỡng đặt trên sub-metric gắn tag scenario: `http_req_duration{scenario:measure}` (p95) và `http_req_failed{scenario:measure}`. Ngưỡng p95 đọc từ `P95_MS`, nên cùng một kịch bản dùng cho mọi service và SLO được ghi ở một chỗ (biến CI).

k6 thoát mã 99 khi một ngưỡng bị vi phạm, nên bước này gắn được vào pipeline và chặn deploy.

## Vì sao cấu hình thế này

- **Open model.** Với VU cố định, service chậm làm mỗi VU gửi ít hơn, tải tự giảm và p95 trông đẹp hơn thực tế. `constant-arrival-rate` giữ nhịp đến, nên khi service chậm hàng đợi thật dài ra và p95 phản ánh điều người dùng thấy. Cần `preAllocatedVUs` đủ lớn: thiếu VU thì k6 bỏ request và tăng `dropped_iterations`.
- **Warmup ngoài ngưỡng.** Đuôi độ trễ lúc mới khởi động là một vấn đề khác (kiểm bằng cổng riêng) và không nên làm ngưỡng p95 của trạng thái ổn định lúc đỏ lúc xanh.
- **Checks trên nội dung.** Một service trả 200 kèm thân rỗng vẫn qua nếu chỉ kiểm mã trạng thái.

## Đọc kết quả

`http_req_duration` p95 so với ngưỡng; `http_reqs` (số thật gửi, so với 30 x 8 + 10 x 3 = 270); `http_req_failed`; `checks`; `dropped_iterations` (nếu khác 0 thì máy sinh tải hay service không theo kịp). k6 chạy cùng máy với service (`--network host`) nên số đo mang tính tương đối: đủ để bắt service chậm gấp ba, không đủ để cam kết SLO.

## Lỗi hay gặp

Đặt ngưỡng bằng số quan sát được lần đầu (ngưỡng sinh ra từ dữ liệu, không từ SLO); quên rằng `thresholds` không có sub-metric thì không có `scenario` trong summary; không đặt tên scenario trùng `exec`.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Cổng thật sự chặn | Service chậm cho mã 99, service khoẻ mã 0 |
| Ngưỡng đúng chỗ | Chỉ trên `scenario:measure`, đọc từ `P95_MS` |
| Đọc được kết quả | Giải thích p95, thông lượng, lỗi, dropped_iterations |
