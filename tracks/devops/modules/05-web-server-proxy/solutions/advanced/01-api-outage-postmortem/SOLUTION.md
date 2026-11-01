# Lời giải: postmortem sự cố API 502 sau CHG-3107

Bài Advanced không có một đáp án duy nhất. Dưới đây là chẩn đoán từ bằng chứng, các quyết định khi viết, rubric, và một
postmortem mẫu đã chạy qua test (đặt vào `starter/POSTMORTEM.md` thì `test_postmortem_document` pass).

## Chẩn đoán từ bằng chứng

| Kết luận | Bằng chứng |
| --- | --- |
| Lỗi 1: upstream trỏ cổng 8080, API production nghe 8000 → `Connection refused` → 502 | `chg-3107.diff` đổi `:8000` thành `:8080`; ghi chú PR "staging chạy API trên 8080... prod vẫn 8000"; `nginx-error.log` dòng `connect() failed (111: Connection refused) ... upstream: "http://10.0.20.11:8080/..."` |
| `max_fails` rút cả hai backend, sau đó `no live upstreams` | `nginx-error.log`: `upstream server temporarily disabled`, rồi `no live upstreams` |
| Lỗi 2: `proxy_pass http://olist_api;` không có URI nên API nhận `/api/orders/...`, không có route → 404 | `nginx-error.log` đã cho thấy `upstream: ".../api/cart"`; chat 14:33–14:35 (404, "path dạng /api/orders/..."); `access-summary.txt` 14:30–14:40 cột 404 tăng vọt, 502 về 0 |
| Lỗi 2 chỉ lộ ra sau khi sửa lỗi 1 | Khi kết nối bị từ chối, request không tới API nên API không có cơ hội trả 404 |
| Lỗi 3 (che sự cố): `/healthz` trả thẳng từ Nginx | Diff thay `proxy_pass .../healthz` bằng `return 200 "ok\n"`; `lb-healthcheck.txt` 2/2 healthy suốt sự cố |
| `nginx -t` không thể bắt | `ci-pipeline.log`: lint chỉ chạy `nginx -t` với `/etc/hosts` giả, không có smoke test |
| Cảnh báo không kêu | `lb-healthcheck.txt`: cảnh báo 5xx chỉ cho lỗi của chính LB, không cho target 5xx |
| Rollback API vô ích, tốn 7 phút | Chat 14:14 (log API không có request), 14:20–14:27 |

Log Nginx ghi UTC (`17:02` = `14:02` São Paulo). Postmortem tốt quy đổi về một múi giờ và ghi rõ.

Số liệu: 14:02–14:44 là 42 phút; 252.400 trên 371.200 request (68%) lỗi, gần như toàn bộ request `/api/*`; đơn hoàn tất 412
so với 1.180 trung bình, hụt 768 đơn, khoảng 122.900 BRL (768 x 160) doanh thu bị lùi hoặc mất; 37 webhook thanh toán bị
502, đối tác tự retry thành công. Time to detect (lỗi đầu tiên tới mở SEV-2): 16 phút. Time to resolve: 42 phút.

## Yếu tố góp phần (chỗ ăn điểm nhất)

- Cấu hình Nginx sao tay từ staging; giá trị phụ thuộc môi trường (cổng) không phải là biến. Staging và production lệch
  nhau từ tháng 9 mà không ai ghi nhận.
- Pipeline chỉ có `nginx -t`; không dựng Nginx thật với upstream giả để gọi thử các route quan trọng; không có smoke test
  sau deploy; staging và production deploy cùng lúc nên staging không phải là một bước chặn.
- Rollout cả hai máy cùng lúc, không canary, không tự rollback khi tỉ lệ 5xx của target tăng.
- Health check của LB trả từ Nginx, không chạm tới API: "xanh" chỉ có nghĩa là tiến trình Nginx còn sống.
- Cảnh báo 5xx không đo response của target; tín hiệu đầu tiên đến từ Sentry của frontend và CSKH.
- PR do lead frontend duyệt; thay đổi routing của edge không có reviewer từ team vận hành (thiếu CODEOWNERS cho thư mục
  `nginx/`).
- Chẩn đoán theo giả định "502 là API chết" dẫn tới rollback API; error log Nginx, nơi có câu trả lời trong 1 dòng, chỉ được
  đọc sau 11 phút.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Hai nguyên nhân kỹ thuật đúng, có bằng chứng | 20 | Nêu cổng 8080/8000 và `proxy_pass` không URI, trích dòng log hoặc diff cho từng lỗi |
| Giải thích vì sao lỗi 2 chỉ lộ sau lỗi 1, và vai trò của `max_fails` | 10 | Kết nối bị từ chối thì API không thấy request; `no live upstreams` |
| Nhận ra lỗi 3 che sự cố | 10 | `/healthz` trả từ Nginx, LB xanh, không ai bị page |
| Tác động định lượng | 10 | 42 phút, khoảng 68% request lỗi, 768 đơn hụt và doanh thu ước tính, 37 webhook, ai không bị ảnh hưởng (trang tĩnh) |
| Dòng thời gian | 10 | Có deploy, lỗi đầu, Sentry, CSKH, SEV-2, rollback API sai hướng, đọc log, hai lần hotfix, xác nhận; quy đổi UTC; tính TTD và TTR |
| Yếu tố góp phần và phát hiện | 15 | `nginx -t` chỉ kiểm cú pháp, không smoke test, cấu hình sao tay theo môi trường, rollout không canary, cảnh báo không đo target 5xx |
| Việc cần làm | 20 | Cụ thể, kiểm được, có người và hạn; có ít nhất một việc pipeline chặn được lỗi (smoke test với upstream thật hoặc giả) và một việc phát hiện trong vài phút (cảnh báo target 5xx, health check đi tới API) |
| Blameless và rõ ràng | 5 | Không đổ cho người duyệt PR hay người deploy; người ngoài team đọc hiểu |

Trừ điểm: kết luận "do API 1.9.3" hoặc "do LB" (−15); việc cần làm kiểu "review kỹ hơn", "cẩn thận khi chép cấu hình" (−10);
chỉ nêu một trong hai lỗi kỹ thuật (−10); trộn giờ UTC và giờ địa phương trong dòng thời gian (−3).

## Postmortem mẫu

`````markdown
# Postmortem: API Olist Shop lỗi sau CHG-3107 ngày 2026-10-28

## 1. Tóm tắt

Chiều thứ Tư 28/10, từ 14:02 tới 14:44 (giờ São Paulo, 42 phút), gần như mọi lời gọi API của Olist Shop bị lỗi sau khi
một thay đổi cấu hình Nginx cho frontend mới được triển khai. Khách vào được trang chủ nhưng không xem giỏ hàng, không
đặt được đơn; webhook của cổng thanh toán bị từ chối. Nguyên nhân là hai lỗi trong cấu hình chép từ staging. Hệ thống đã
khôi phục hoàn toàn, đối tác thanh toán đã tự gửi lại webhook.

## 2. Tác động

- 252.400 trên 371.200 request (68%) lỗi trong 42 phút, gần như toàn bộ request tới `/api/*`.
- 14:02–14:31: lỗi 502; 14:31–14:44: lỗi 404.
- Đơn hoàn tất 14:00–15:00: 412 so với trung bình 1.180 cùng giờ bốn thứ Tư trước, hụt 768 đơn, khoảng 122.900 BRL.
- 37 webhook thanh toán bị trả 502, đối tác retry thành công lúc 14:50; không mất giao dịch.
- Không bị ảnh hưởng: trang tĩnh của frontend, worker nền.

## 3. Dòng thời gian

Giờ São Paulo (UTC-3). Log Nginx ghi UTC đã được quy đổi.

| Thời điểm | Sự kiện | Nguồn |
| --- | --- | --- |
| 13:58 | Pipeline #418: `nginx -t` OK, build và push cấu hình CHG-3107 | ci-pipeline.log |
| 14:02 | Reload Nginx trên edge-1, edge-2; change đóng | Chat |
| 14:02 | Lỗi đầu tiên: `connect() failed (111)` tới `:8080`, sau đó `no live upstreams` | nginx-error.log (17:02 UTC) |
| 14:03 | LB báo 2/2 healthy | lb-healthcheck.txt |
| 14:06 | Sentry: 214 lỗi "Failed to load cart: 502" | Chat |
| 14:09 | CSKH báo khách không thêm được hàng vào giỏ | Chat |
| 14:14 | Team API: container chạy, log API không có request | Chat |
| 14:18 | Mở SEV-2 | Chat |
| 14:20 | Rollback API về 1.9.2 (giả thuyết sai) | Chat |
| 14:27 | Rollback xong, vẫn 502 | Chat |
| 14:29 | Đọc error log Nginx, thấy cổng 8080 | Chat, nginx-error.log |
| 14:31 | Hotfix CHG-3110 sửa cổng; 502 hết, xuất hiện 404 | Chat, access-summary.txt |
| 14:35 | Log API cho thấy path `/api/orders/...` | Chat |
| 14:41 | Hotfix CHG-3112 sửa `proxy_pass` | Chat |
| 14:44 | Lỗi frontend về mức nền | Chat |
| 14:50 | Đối tác thanh toán retry 37 webhook thành công | Chat |

Time to detect (lỗi đầu tiên tới SEV-2): 16 phút. Time to resolve: 42 phút.

## 4. Nguyên nhân gốc và yếu tố góp phần

CHG-3107 thay cấu hình Nginx production bằng bản của staging. Bản đó có hai lỗi với production. Thứ nhất, upstream trỏ cổng
8080, nơi API của staging nghe từ tháng 9, trong khi API production vẫn nghe 8000: mọi kết nối bị từ chối (`111: Connection
refused`), Nginx rút cả hai backend theo `max_fails` và trả 502. Thứ hai, khối `location /api/` dùng `proxy_pass
http://olist_api;` không có phần URI, nên Nginx chuyển nguyên `/api/orders/...` cho API, vốn chỉ có route `/orders/...`: API
trả 404. Lỗi thứ hai bị lỗi thứ nhất che: khi kết nối bị từ chối, request không bao giờ tới API, nên chỉ sau hotfix cổng
lúc 14:31 nó mới lộ ra. Cùng change còn đổi `/healthz` thành phản hồi tĩnh của Nginx, nên health check của load balancer
xanh suốt sự cố.

Yếu tố góp phần:

- Cấu hình sao tay giữa môi trường; cổng của API không là biến, staging và production đã lệch nhau mà không ai ghi nhận.
- Pipeline chỉ chạy `nginx -t`, kiểm cú pháp chứ không kiểm Nginx có gọi được API và route đúng không; không có smoke test
  sau deploy.
- Staging deploy cùng lúc với production, rollout hai máy cùng lúc, không canary và không tự rollback.
- Health check của LB không đi tới API; cảnh báo 5xx chỉ đo lỗi của chính LB, không đo response của target.
- Thay đổi routing của edge được duyệt bởi team frontend, không có reviewer từ team vận hành.

## 5. Phát hiện và xử lý

Giám sát không kêu vì health check của load balancer nhận 200 từ chính Nginx và cảnh báo 5xx không tính lỗi do target trả.
Tín hiệu đầu tiên là Sentry của frontend sau 4 phút, rồi CSKH; SEV-2 mở sau 16 phút. Chẩn đoán đi lạc 9 phút vì giả định
"502 là API chết" dẫn tới rollback API, dù team API đã báo log không có request nào. Error log của Nginx chứa câu trả lời
trong một dòng (cổng 8080, path `/api/...`) và được đọc lúc 14:29. Mỗi lỗi được sửa bằng một dòng cấu hình và reload, không
cần downtime.

## 6. Việc cần làm

| Việc | Loại | Người phụ trách | Hạn |
| --- | --- | --- | --- |
| Pipeline dựng Nginx với cấu hình mới và API giả có cùng route, gọi các route chính, chặn merge khi khác 2xx | phòng ngừa | Team platform | 2026-11-11 |
| Smoke test sau reload trên từng máy (`/api/healthz`, một route đọc), tự rollback khi lỗi | phòng ngừa | Team platform | 2026-11-11 |
| Sinh cấu hình Nginx từ template, cổng và upstream theo biến môi trường; xoá bản sao tay | phòng ngừa | Team platform | 2026-11-25 |
| Health check của LB gọi `/healthz` của API qua Nginx | phát hiện | SRE | 2026-11-04 |
| Cảnh báo tỉ lệ 5xx của target trên 2% trong 2 phút, page on-call | phát hiện | SRE | 2026-11-04 |
| Rollout cấu hình edge từng máy, chờ 5 phút giữa hai máy | giảm thiểu | Team platform | 2026-11-18 |
| CODEOWNERS cho `nginx/`, bắt buộc một reviewer team vận hành | phòng ngừa | Lead platform | 2026-11-06 |
| Runbook 5xx: đọc error log Nginx trước khi rollback app | giảm thiểu | On-call lead | 2026-11-06 |

## 7. Bài học

- `nginx -t` chỉ chứng minh cấu hình đọc được; chỉ có gọi thử thật mới chứng minh nó đúng.
- Health check phải đi qua đúng đường người dùng đi; health check trả từ proxy chỉ chứng minh proxy còn sống.
- Với 5xx ở proxy, error log của proxy nói chính xác nó đã gọi tới đâu; đọc nó trước khi đoán và rollback.
`````
