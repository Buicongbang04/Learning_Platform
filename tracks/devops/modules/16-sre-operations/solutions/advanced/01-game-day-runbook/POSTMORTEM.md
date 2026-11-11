# Postmortem: game day Olist Shop, seed 18

## 1. Tóm tắt

Game day ngày 2026-11-11 trên lab, seed 18. Sau khi xác nhận trạng thái ổn định, injector làm mọi gói tin rời container API chậm thêm
400 ms. Khách tra đơn thấy mỗi trang mất gần một giây, không có lỗi 5xx nên một alert theo tỉ lệ lỗi sẽ không bắn. Runbook phát hiện
bằng p95 của route tra đơn sau khoảng 27 giây và khôi phục bằng restart API. Game day xác nhận runbook đủ cho lỗi này nhưng chỉ ra
rằng dashboard chưa giúp phân biệt "API chậm" với "Postgres chậm".

## 2. Tác động

Khoảng 30 giây (từ lúc bơm tới khi API khởi động lại), mọi request chậm gấp khoảng 20 lần, không request nào lỗi. Theo SLO latency 95%
dưới 250 ms trong 30 ngày, ở traffic thật khoảng 8 rps đây là chừng 240 request xấu, tức khoảng 0,02% error budget của tháng. SLO
availability không bị ảnh hưởng.

## 3. Timeline

| Giờ | Sự kiện |
| --- | --- |
| 10:15:02 | Stack lên, traffic giả bắt đầu |
| 10:15:22 | Trạng thái ổn định 10 giây liên tục, không entry nào khớp |
| 10:15:32 | Injector bơm lỗi |
| 10:15:59 | Entry `api-slow` khớp |
| 10:16:00 | Chạy restart api |
| 10:16:12 | Traffic khoẻ 10 giây liên tục, kết thúc game day |

## 4. Nguyên nhân

- Độ trễ mạng ở phía API (mô phỏng NIC hay node có vấn đề): mọi lời gọi từ API tới Postgres, Redis và mọi response đều chậm thêm.
- Không có gì trong hệ thống tự phát hiện API chậm: không alert latency, không probe tổng hợp, chỉ có alert theo lỗi.

## 5. Phát hiện và khôi phục

Entry `api-slow` (p95 route tra đơn trên 300 ms trong 1 phút) phát hiện sau khoảng 27 giây; cửa sổ `rate` 1 phút cộng chu kỳ scrape
5 giây là phần lớn độ trễ. Hành động restart api tạo lại network namespace của container nên độ trễ biến mất; API sẵn sàng lại sau
khoảng 3 giây.

## 6. Bài học

- Latency phải có SLO và alert riêng: lỗi làm chậm mà không làm hỏng là loại khách cảm nhận rõ nhất mà alert theo lỗi bỏ sót.
- Thứ tự entry quan trọng: route tra đơn chỉ chạm Postgres nên dùng được để tách "API chậm" khỏi "Redis chậm".
- Restart xoá luôn bằng chứng; runbook phải lưu trace và log trước khi hành động.

## 7. Action items

| Việc | Người phụ trách | Hạn |
| --- | --- | --- |
| Thêm burn-rate alert cho SLO latency của route tra đơn | Team checkout | 2026-11-25 |
| Panel so sánh p95 theo route và span DB trên dashboard RED | Team platform | 2026-11-20 |
| Bước "lưu trace và log" bắt buộc trước restart trong mọi runbook | Người viết runbook | 2026-11-18 |
| Game day lặp lại hằng tháng với seed ngẫu nhiên | Incident commander tháng 12 | 2026-12-09 |
