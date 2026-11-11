# Postmortem: Redis dừng đột ngột, đẩy job tính lại doanh thu hỏng 21 giây, game day seed 214650

Trạng thái: hoàn tất. Người viết: người trực game day. Ngày: 2026-11-11. Không đổ lỗi: bài này tả hệ thống và quy trình, không tả ai
sai.

Trước game day (viết trước khi chạy):

- Giả thuyết trạng thái ổn định: mọi request của khách giả đạt (đúng mã, dưới 0,5 giây), khoảng 4 lượt mỗi giây; tỉ lệ lỗi SLI
  `olist:slo_api_errors:ratio_rate5m` bằng 0; không entry nào của `runbook.yaml` khớp.
- Blast radius: một lỗi trong `api`, `postgres` hoặc `redis` của stack test, hoàn tác khi test kết thúc; không chạm stack khác trên máy.
- Điều kiện dừng: test chạy quá 6 phút, hay thấy container nào ngoài lab của test đổi trạng thái thì Ctrl-C.
- Vai trò: làm một mình, đóng cả người chỉ huy, người thao tác (runbook máy chạy) và người ghi chép (Grafana, đồng hồ).

## 1. Tóm tắt

Game day seed 214650 trên stack production M03 cộng observability M08. Lỗi được bơm là Redis dừng đột ngột (kill từ ngoài container).
API vẫn sống, tra đơn vẫn nhanh, nhưng `POST /jobs/recompute` trả 503 "redis unavailable" và `/readyz` báo `"redis": "error"`. Entry
`queue-errors` phát hiện sau 10 giây và chạy `restart redis`; hệ thống khoẻ 10 giây liền ở giây 21 sau khi bơm. Job đã xếp hàng trước sự
cố nằm trong AOF nên không mất; worker tự nối lại và xử lý tiếp. Alert SLO không bắn, đúng thiết kế: 21 giây lỗi ở một route không đủ đốt
2% budget trong một giờ.

## 2. Tác động

- Thời lượng: 21 giây từ lúc Redis chết tới lúc khoẻ lại (10 giây phát hiện, 11 giây từ lúc restart tới khi mọi route đạt liền 10 giây
  tính từ hành động).
- Khách giả: 60 trên 213 request hỏng (28%) từ lúc bơm tới hết cửa sổ khoẻ; gồm `/readyz` 503 (không tính vào SLI) và đẩy job 503.
  Tra đơn không hỏng request nào.
- SLI `api-availability`: route đẩy job chiếm khoảng 1/5 request của khách (bốn lượt tra đơn mỗi một job), hỏng hoàn toàn 21 giây, tương
  đương khoảng 21 × 0,2 = 4 giây ngừng toàn phần, tức 0,07 phút trên 216 phút error budget 30 ngày: **khoảng 0,03% budget đã tiêu**.
- Dữ liệu: không mất job (AOF trên volume `redisdata`); bảng doanh thu theo bang trễ cập nhật khoảng 20 giây.

## 3. Timeline

Giờ theo đồng hồ máy chạy test; giây sau khi bơm lấy từ dòng tóm tắt của test.

| Giờ | Sự kiện |
| --- | --- |
| 10:52:10 | Stack game day lên; test in địa chỉ Grafana, mở dashboard Olist Shop |
| 10:52:31 | Khách giả khoẻ 10 giây liền; test kiểm trạng thái ổn định: rule SLO nạp đủ, không entry nào khớp |
| 10:52:51 | Bơm lỗi (giây 0). Panel tỉ lệ lỗi 5xx của `/jobs/recompute` bắt đầu lên trong lần scrape kế tiếp |
| 10:53:01 | Giây 10: `queue-errors` khớp (`sum(rate(...path="/jobs/recompute", status=~"5.."}[30s])) > 0`), chạy `restart redis` |
| 10:53:03 | Redis chạy lại, nạp AOF; `/readyz` về 200, đẩy job về 202 |
| 10:53:12 | Giây 21: mọi route đạt 10 giây liền kể từ hành động; test coi là đã khôi phục |
| 10:53:30 | `jobs_processed_total` của worker tăng thêm hơn 3 job; dashboard trở lại bình thường |

## 4. Nguyên nhân và yếu tố góp phần

- Nguyên nhân trực tiếp: tiến trình Redis bị kill từ ngoài container (lỗi bơm của game day; ngoài đời là OOM killer của host, người thao
  tác nhầm, hay node bị thu hồi).
- Restart policy `unless-stopped` không dựng lại container bị kill từ ngoài: Docker coi đó là dừng có chủ đích. Không có gì tự khôi phục;
  cần một hành động, và hành động đó chờ tới khi runbook phát hiện.
- Redis là một điểm hỏng duy nhất của đường đẩy job: không có bản sao, API không có hàng đợi dự phòng hay retry phía client.
- Yếu tố giảm nhẹ: API trả 503 nhanh (timeout kết nối Redis 1 giây) thay vì treo, nên tra đơn không bị kéo theo; AOF giữ job.

## 5. Phát hiện

- Tín hiệu thấy trước: panel 5xx theo path của dashboard, ngay lần scrape đầu sau sự cố. Log API có "không đẩy được job vào redis".
- Entry đã chạy: `queue-errors`, đúng thành phần ngay lần đầu; các entry đứng trước (`api-unreachable`, `api-network-slow`, `db-errors`,
  `db-slow`) không khớp vì API sống và tra đơn bình thường.
- Alert: `OlistApiErrorBudgetBurn` không bắn (cần tỉ lệ lỗi 1 giờ trên 7,2%); `OlistApiHighErrorRate` của M08 không bắn (`for: 5m`).
  Đúng thiết kế cho một sự cố 21 giây, nhưng nghĩa là nếu runbook máy không chạy thì không ai được gọi trước 5 phút. Không có alert nào
  cho "Redis không trả lời".

## 6. Điều làm tốt, điều chưa tốt, điều may mắn

- Làm tốt: entry tách theo route nên chỉ ra đúng Redis, không restart nhầm Postgres hay API.
- Làm tốt: AOF trên volume giữ được job; worker tự nối lại, không cần restart worker.
- Chưa tốt: thời gian phát hiện 10 giây chủ yếu là chờ scrape và cửa sổ `[30s]`; một alert dựa trên `/readyz` từ blackbox probe sẽ nhanh
  hơn và không phụ thuộc API còn sống.
- Chưa tốt: không có metric độ dài hàng đợi `olist:jobs`, nên không đo được có bao nhiêu job dồn lại trong sự cố.
- May mắn: lỗi rơi vào Redis, thành phần rẻ nhất để restart; cùng loại lỗi với Postgres sẽ làm hỏng hành trình chính.

## 7. Action item

| Việc | Người phụ trách | Hạn | Loại |
| --- | --- | --- | --- |
| Thêm alert `OlistRedisDown` (page) từ redis_exporter hay blackbox probe `/readyz`, `for: 30s`, trỏ runbook `queue-errors` | Người trực tuần này | 2026-11-18 | Phát hiện |
| Thêm metric độ dài hàng đợi `olist:jobs` (exporter hay gauge ở worker) và panel trên dashboard | Chủ service Olist Shop | 2026-11-25 | Phát hiện |
| Thử retry có giới hạn (1 lần, 200 ms) cho `rpush` trong API, đo lại game day cùng seed | Chủ service Olist Shop | 2026-11-25 | Giảm nhẹ |
| Đánh giá Redis có bản sao (Sentinel hay dịch vụ quản lý khi lên cloud) và ghi quyết định vào README | Người trực tuần này | 2026-12-09 | Phòng ngừa |

## 8. Các game day

| Seed | Lỗi | Entry đã chạy | Phát hiện sau | Khoẻ lại sau | Sửa gì sau lần này |
| --- | --- | --- | --- | --- | --- |
| 214650 | Redis bị kill | `queue-errors` (restart redis) | 10 giây | 21 giây | Thêm action item 1 và 2; chưa đổi runbook |
| 4 | Postgres bị kill | `db-errors` (restart postgres) | 10 giây | 23 giây | Không đổi; ghi vào `db-errors` rằng API trả 500 ngay vì tên `postgres` không còn phân giải được |
| 12 | Mạng của Postgres chậm | `db-slow` (restart postgres) | 19 giây | 32 giây | Phát hiện chậm nhất trong các lần: p95 trên cửa sổ `[30s]` cần đủ mẫu chậm. Giữ ngưỡng 0,3 giây (hạ xuống thì báo động giả lúc máy bận), thêm action item theo dõi |
