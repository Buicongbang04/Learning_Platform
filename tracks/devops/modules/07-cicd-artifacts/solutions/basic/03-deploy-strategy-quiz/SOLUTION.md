# Lời giải: chọn chiến lược deploy và rollback

| Câu | Đáp án | Ràng buộc quyết định |
| --- | --- | --- |
| `risky-pricing-change` | b. Canary có phân tích metric | Đo bản mới trên một phần nhỏ traffic thật, tự quay lại theo ngưỡng |
| `protocol-switch` | c. Blue/green | Không được trộn phiên bản; cần quay lại trong vài giây; có dư tài nguyên |
| `exclusive-worker` | a. Recreate | Hai bản không được chạy cùng lúc; chậm vài phút chấp nhận được |
| `launch-date` | d. Feature flag | Tách deploy khỏi release; bật theo vùng |
| `rename-column` | b. Expand/contract qua nhiều release | Rolling update luôn có lúc hai bản cùng đọc ghi một schema |
| `fastest-rollback` | c. Deploy lại digest trước | Artifact có sẵn, bất biến, đã chạy tốt |
| `canary-within-threshold` | b. Sang bước tiếp theo | Kết quả nằm trong ngưỡng đã thống nhất trước |
| `mirror-traffic` | a. Shadow traffic | Đo trên traffic thật mà khách không nhận response của bản mới |
| `zero-downtime-rolling` | a, b, c | Readiness đúng, dừng êm, schema tương thích hai chiều |

## Giải thích từng câu

### `risky-pricing-change`: canary có phân tích metric

Canary đưa một tỉ lệ traffic (theo request, không theo số pod) vào bản mới, so metric với bản cũ (baseline) và tự quay lại khi vượt
ngưỡng: Argo Rollouts `AnalysisTemplate`, Flagger, hay rollout theo trọng số của service mesh và load balancer. Rolling update (a)
cũng có lúc hai bản cùng chạy, nhưng tỉ lệ theo số pod, tiến tới 100% bất kể metric, và "xem dashboard sau khi xong" là phát hiện
lỗi khi mọi người dùng đã dính. Blue/green (c) đổi toàn bộ một lần: lỗi logic phí vận chuyển đến tay mọi khách cùng lúc. Recreate (d)
có downtime và vẫn đưa bản mới cho tất cả.

### `protocol-switch`: blue/green

Khi hai phiên bản **không được** cùng nhận request, mọi chiến lược trộn phiên bản (rolling, canary) đều sai. Blue/green dựng môi
trường mới đầy đủ (xanh), kiểm nó khi chưa có traffic, rồi đổi router một lần; rollback là đổi router lại, tính bằng giây, vì môi
trường cũ vẫn chạy. Cái giá là gấp đôi tài nguyên trong lúc chuyển, và phiên làm việc đang dở (session, websocket) phải được xử lý
khi đổi. Feature flag (d) chỉ đúng nếu cả hai định dạng token được hỗ trợ song song trong code, mà đề bài nói không phải vậy.

### `exclusive-worker`: recreate

Recreate dừng hết bản cũ rồi mới khởi động bản mới (Kubernetes `strategy.type: Recreate`). Có một khoảng không có worker nào chạy,
với job theo lô thì vô hại. Rolling với `maxSurge: 1` (c) tạo pod mới trước khi xoá pod cũ: đúng lúc đó hai bản ghi đè nhau. Canary
(b) và blue/green giữ cả hai nhóm cùng chạy (d) cũng vậy. Nếu không chấp nhận khoảng trống, cách đúng là sửa worker để dùng khoá
phân tán (lease) chứ không phải chọn chiến lược khác.

### `launch-date`: feature flag

Deploy là đưa code lên production; release là bật cho người dùng. Feature flag tách hai việc: code mới đi theo mỗi lần deploy hằng
ngày nhưng tắt, ngày ra mắt bật theo vùng mà không deploy gì (LaunchDarkly, Unleash, Flagsmith, OpenFeature làm chuẩn API). Nhánh
dài hạn (a) là đúng thứ trunk-based muốn tránh: merge lớn, xung đột, rủi ro dồn vào một ngày. Môi trường xanh tắt (b) hay canary 0%
(c) giữ một bản deploy riêng 2 tuần, chặn mọi deploy khác. Flag cũng là nợ: đặt hạn xoá flag sau khi bật 100%.

### `rename-column`: expand/contract

Trong rolling update luôn có lúc pod cũ và pod mới cùng chạy, nên schema phải dùng được cho cả hai. Đổi tên cột trong một release
(a) làm pod cũ lỗi ngay khi migration chạy. Cách đúng chia nhiều release: (1) **expand**: thêm cột `state`, code ghi cả hai cột;
(2) backfill dữ liệu cũ; (3) code đọc từ `state`; (4) **contract**: bỏ ghi cột cũ, rồi xoá cột. Mỗi bước rollback được về bước
trước. Blue/green (c) không cho mỗi môi trường một cơ sở dữ liệu riêng một cách tự nhiên: hai môi trường thường dùng chung DB, nên
vấn đề y nguyên. Chặn ghi (d) chính là downtime.

### `fastest-rollback`: deploy lại digest trước

Image của bản trước đã nằm trong registry, đã chạy tốt, digest không đổi được: deploy lại nó mất đúng thời gian một lần rollout
(`kubectl rollout undo`, `argocd app rollback`, hay đổi digest trong manifest). `git revert` (a) và build lại (b) phải chờ CI, và
build lại không đảm bảo ra đúng image cũ (image nền, dependency đã đổi). Dời `latest` (d) không làm node nào kéo lại (pod đang chạy
không tự pull), và mỗi node có thể giữ một bản `latest` khác nhau. Đó là lý do lịch sử deploy phải ghi digest.

### `canary-within-threshold`: sang bước tiếp theo

Lỗi 0,42% so với 0,35% là tăng 0,07 điểm phần trăm, trong ngưỡng 0,5; p95 tăng 3%, trong ngưỡng 10%; mẫu đủ. Kế hoạch đã nói làm
gì: sang bước tiếp (ví dụ 25%). Rollback (a) vì "cao hơn baseline" làm canary vô nghĩa: hai bản không bao giờ có số giống hệt nhau.
Nhảy thẳng 100% (c) bỏ qua các bước còn lại, nơi lỗi chỉ lộ ra ở tải cao. Họp để quyết bằng cảm nhận (d) là lý do ngưỡng phải viết
ra trước: quyết định lúc 2 giờ sáng không nên phụ thuộc người đang trực.

### `mirror-traffic`: shadow traffic

Shadow (mirror) gửi một bản sao request thật tới bản mới và bỏ response của nó (Istio `mirror`, Envoy `request_mirror_policies`,
Nginx `mirror`). Đo được độ trễ, lỗi, so kết quả với bản cũ mà không khách nào bị ảnh hưởng. Cẩn thận với request có tác dụng phụ:
bản shadow không được ghi vào DB thật hay gửi email. Canary (b), blue/green (c), A/B test (d) đều để khách nhận response của bản mới;
A/B test còn là thí nghiệm sản phẩm, không phải kỹ thuật deploy.

### `zero-downtime-rolling`: a, b, c

- (a) Readiness probe quyết định khi nào pod mới được đưa vào Service; probe báo sẵn sàng quá sớm thì request rơi vào pod chưa nạp
  xong.
- (b) Pod cũ nhận SIGTERM trong khi vẫn còn request đang xử lý (và vài giây request mới, trước khi endpoint được gỡ). App phải dừng
  êm, thường kèm `preStop` chờ vài giây (module 06 mục 4, module 11).
- (c) Hai bản cùng chạy trên một schema (câu `rename-column`).
- (d) sai: `latest` không làm rolling update xảy ra (spec không đổi thì không có rollout) và làm mỗi node có thể chạy bản khác nhau.
- (e) sai: `maxUnavailable: 100%` cho phép xoá mọi pod cũ trước khi pod mới sẵn sàng, tức là downtime.
