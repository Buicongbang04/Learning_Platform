# Câu hỏi phỏng vấn: Service mesh và cloud design patterns

## Service mesh là gì? Data plane và control plane khác nhau thế nào?

Service mesh là một lớp hạ tầng lo giao tiếp giữa các service: mã hoá và xác thực (mTLS), retry, timeout, chia traffic, và số liệu về
mọi lời gọi, mà không phải sửa code ứng dụng.

- **Data plane**: các proxy đứng cạnh từng workload (sidecar) hay từng node; mọi request thật đi qua chúng. Linkerd dùng `linkerd2-proxy`
  (Rust), Istio và Consul dùng Envoy.
- **Control plane**: phát cấu hình cho proxy (endpoint của Service, policy, route) và cấp chứng chỉ. Nó không nằm trên đường đi của
  request: control plane chết thì proxy vẫn chạy với cấu hình cuối, chỉ thay đổi mới bị kẹt.

Câu hỏi tiếp theo hay gặp: "control plane chết thì sao?". Trả lời: traffic đang có vẫn chạy; pod mới không được inject (webhook
`failurePolicy: Ignore` thì pod chạy không proxy), chứng chỉ không được gia hạn, nên sau tối đa thời hạn chứng chỉ (24 giờ ở Linkerd)
mTLS bắt đầu hỏng.

## Sidecar và ambient khác nhau thế nào? Khi nào chọn cái nào?

Sidecar đặt một proxy trong mỗi pod; ambient (Istio) đặt một proxy L4 (`ztunnel`) mỗi node lo mTLS và policy theo danh tính, và chỉ dựng
proxy L7 (`waypoint`) cho namespace hay service cần retry, route theo header.

| | Sidecar | Ambient |
| --- | --- | --- |
| Tài nguyên | Tỉ lệ số pod | Tỉ lệ số node cộng số waypoint |
| Nâng cấp proxy | Restart pod của ứng dụng | Restart ztunnel, không đụng pod |
| Cô lập lỗi | Một proxy hỏng ảnh hưởng một pod | ztunnel hỏng ảnh hưởng cả node |
| Độ chín | Lâu đời | Mới hơn (GA ở Istio 1.24, cuối 2024) |

Chọn ambient khi số pod lớn, RAM là vấn đề, đa số service chỉ cần mTLS. Chọn sidecar khi cần cô lập theo workload, hay dùng mesh chỉ có
sidecar (Linkerd). Native sidecar của Kubernetes 1.29+ giải được hai phiền toái cũ của sidecar: thứ tự khởi động và Job không kết thúc.

## mTLS trong mesh hoạt động thế nào? Danh tính của một pod là gì?

Mỗi proxy sinh khoá riêng trong bộ nhớ, gửi CSR kèm token ServiceAccount tới CA của mesh (`linkerd-identity`). CA kiểm token bằng
TokenReview, cấp chứng chỉ có tên theo ServiceAccount (`api.olist.serviceaccount.identity.linkerd.cluster.local`), hạn ngắn (24 giờ),
proxy tự xoay. Khi hai proxy nói chuyện, cả hai trình chứng chỉ, nên server biết chắc ai đang gọi.

Danh tính gắn với ServiceAccount chứ không với IP hay nhãn: IP của pod đổi liên tục, nhãn thì ai tạo được pod cũng đặt được. Muốn mang
danh tính `api` phải có quyền chạy pod bằng ServiceAccount `api` trong đúng namespace.

Chuỗi tin cậy: trust anchor (CA gốc, giữ ngoài cluster) ký issuer (CA trung gian trong cluster), issuer ký chứng chỉ proxy. Trust anchor
hết hạn là sự cố toàn mesh; phải có lịch xoay và cảnh báo.

## NetworkPolicy và AuthorizationPolicy của mesh khác nhau thế nào? Có cần cả hai không?

NetworkPolicy lọc ở tầng mạng (L3/L4) theo IP, nhãn pod, namespace; CNI thực thi; không mã hoá, không biết ai thật sự đang gọi. Policy của
mesh xác thực danh tính bằng mật mã và hiểu HTTP (cho phép theo path, method), nhưng chỉ chặn được traffic đi qua proxy.

Cần cả hai: NetworkPolicy là lớp nền (chặn cả traffic đi vòng proxy, chặn egress ra Internet), mesh là lớp danh tính và mã hoá. Đây là
defense in depth: một lớp cấu hình sai thì lớp kia vẫn giữ.

## Retry có thể làm sự cố tệ hơn thế nào? Làm sao retry an toàn?

Retry là tải thêm. Khi backend hỏng hẳn, một tầng thử n lần nhân tải lên n; nhiều tầng nối tiếp thì nhân với nhau. Backend đang chậm vì
quá tải nhận thêm tải đúng lúc yếu nhất, chậm hơn, gây thêm timeout và thêm retry: vòng lặp tự duy trì (retry storm, metastable failure),
có thể kéo dài cả khi nguyên nhân ban đầu đã hết.

Retry an toàn:

- Chỉ cho lỗi tạm thời (503, 429, timeout, mất kết nối), không cho 4xx hay phần lớn 500.
- Chỉ cho request idempotent, hay có idempotency key.
- Chỉ ở một tầng; giới hạn số lần thử; retry budget theo tỉ lệ.
- Backoff theo cấp số nhân có jitter; tôn trọng `Retry-After`.
- Kết hợp circuit breaker để ngừng hẳn khi lỗi liên tục, và deadline cho cả lời gọi.

## Full jitter là gì, vì sao cần?

Exponential backoff không jitter: mọi client lỗi cùng lúc sẽ chờ cùng 1, 2, 4 giây rồi cùng thử lại, tạo các đợt tải đồng bộ (thundering
herd). Full jitter lấy thời gian chờ ngẫu nhiên đều trong khoảng từ 0 tới mức backoff (`random.uniform(0, min(cap, base * 2^attempt))`),
dàn đều tải theo thời gian. Bài viết "Exponential Backoff and Jitter" của AWS cho thấy full jitter vừa giảm tổng số lần gọi vừa giảm thời
gian hoàn thành so với không jitter. Trong test, truyền `rng` có seed và đồng hồ giả vào để kết quả lặp lại được.

## Timeout nên đặt thế nào trong một chuỗi gọi nhiều tầng?

- Mọi lời gọi ra ngoài đều có timeout; mặc định "không giới hạn" của nhiều thư viện là lỗi chờ ngày xảy ra.
- Đặt theo số đo: p99 thật của dependency cộng một khoảng, không đoán.
- Tầng ngoài lớn hơn tầng trong cộng thời gian retry của tầng trong; nếu không, tầng ngoài bỏ cuộc trong khi tầng trong vẫn làm việc vô
  ích.
- Phân biệt timeout mỗi lần thử (cắt lần treo để thử lại) và timeout cả request (trần cho người gọi). Ở Linkerd là
  `retry.linkerd.io/timeout` và `timeout.linkerd.io/request`.
- Tốt nhất là truyền deadline: tầng dưới biết còn bao nhiêu thời gian và bỏ việc khi người gọi đã bỏ (gRPC có sẵn).

## Circuit breaker hoạt động thế nào? Nó khác retry ở đâu?

Ba trạng thái. Đóng: gọi bình thường, đếm lỗi liên tiếp. Đạt ngưỡng thì Mở: mọi lời gọi bị từ chối ngay, không tới dependency. Hết thời
gian chờ thì Nửa mở: cho một request thử; thành công thì Đóng, thất bại thì Mở lại.

Retry đánh cược lỗi là tạm thời và thử lại; circuit breaker kết luận lỗi không tạm thời và ngừng gọi, để dependency có thời gian hồi phục
và để người gọi trả lỗi nhanh (hay fallback) thay vì chờ timeout. Dùng cùng nhau: breaker bọc ngoài, khi mở thì cắt luôn vòng retry.

Chi tiết dễ sai: 4xx không nên đếm là lỗi (dependency vẫn trả lời đúng); breaker phải theo từng dependency; nửa mở chỉ cho một request
thử, không cho cả đợt.

## Bulkhead giải quyết vấn đề gì? Cho ví dụ.

Lỗi lan qua tài nguyên dùng chung. Nếu mọi lời gọi ra ngoài dùng chung một pool thread hay kết nối, một dependency treo giữ hết pool, và
những trang không cần dependency đó cũng chết. Bulkhead chia tài nguyên thành ngăn riêng (như vách ngăn của tàu): pool kết nối riêng có
giới hạn cho dịch vụ báo giá vận chuyển của đối tác, tách khỏi pool Postgres của đơn hàng. Đối tác treo thì chỉ ngăn của nó đầy; trang
đơn hàng vẫn chạy. Ở mức hạ tầng: tách node pool, ResourceQuota theo namespace, hàng đợi riêng cho từng loại job.

## Idempotency key là gì? Phía server phải làm gì?

Client sinh một key duy nhất cho mỗi thao tác có tác dụng phụ (tạo thanh toán), gửi trong header (`Idempotency-Key`) và gửi lại đúng
key đó ở mọi lần thử. Server lưu key cùng kết quả (bảng có ràng buộc unique, có TTL): gặp key đã có thì trả lại kết quả cũ thay vì làm
lại; cùng key mà body khác thì trả lỗi (409, 422); request cùng key đang xử lý thì trả 409 hay chờ. Nhờ vậy timeout (không biết server đã
làm chưa) có thể retry mà không trừ tiền hai lần. Mesh không làm thay được việc này: proxy không biết hai POST là cùng một thanh toán.

## Khi nào bạn khuyên một team KHÔNG dùng service mesh?

- Ít service, một team, chưa có yêu cầu mTLS: NetworkPolicy, TLS ở ingress, một thư viện client chung là đủ.
- Không ai đọc được metrics, log của proxy; mesh thành hộp đen khi có sự cố.
- Cluster thiếu RAM; workload nhạy độ trễ tới mức thêm vài trăm micro giây mỗi chặng là đáng kể.
- Vấn đề thật nằm ngoài tầng mạng: idempotency, dữ liệu, giao tiếp chủ yếu qua hàng đợi.

Khi nên dùng: yêu cầu mTLS và danh tính từ kiểm toán, nhiều team nhiều ngôn ngữ cần cùng chính sách, cần canary theo tỉ lệ traffic, cần
thấy "ai gọi ai" trên hàng chục service. Đưa vào từng bước, đo, có đường lui.

## So sánh Linkerd, Istio và Consul. Bạn chọn thế nào?

- **Linkerd**: proxy Rust nhỏ, mTLS mặc định, ít CRD, ít tính năng có chủ đích; hợp khi cần mTLS, metrics, retry với ít người vận hành.
  Chỉ Kubernetes. Bản stable do nhà phân phối build, mã nguồn mở chỉ có edge.
- **Istio**: Envoy, tính năng L7 phong phú nhất (mirror, fault injection, rate limit, Wasm), có ambient; cấu hình lớn, cần team
  platform đủ người.
- **Consul**: chạy cả trên VM, Nomad, Kubernetes; tích hợp Vault; hợp hệ thống lai, đổi lại thêm cụm Consul server.
- **Cilium**: nếu đã dùng Cilium làm CNI, có mTLS theo node và L7 qua Envoy theo node, ít proxy.

Chọn theo ràng buộc của tổ chức (người vận hành, phạm vi VM, yêu cầu L7, RAM), không theo bảng tính năng. Và luôn so với phương án
không dùng mesh.

## Làm sao đưa mesh vào production mà không gây sự cố?

1. Staging trước, đo RAM, độ trễ thêm, tỉ lệ thành công.
2. Production theo vùng ảnh hưởng: một namespace ít quan trọng, rồi từng service; inject bằng annotation và `rollout restart`.
3. Xác nhận bằng metrics: kết nối giữa các service đã là `tls="true"`, đúng `client_id`.
4. Policy chặn đến sau cùng: liệt kê đủ bên gọi đã thấy trong metrics, áp từng Server, theo dõi số request bị từ chối.
5. Đường lui đã tập: bỏ annotation inject, restart, xoá policy.
6. Vận hành: ai giữ trust anchor, lịch xoay issuer, lịch nâng cấp proxy (cần restart pod), cảnh báo khi injector chết.

## Kể tên các cloud design pattern theo bốn nhóm và một ví dụ cho mỗi nhóm.

- **Availability**: Retry, Circuit Breaker, Bulkhead, Throttling, Queue-Based Load Leveling, Health Endpoint Monitoring, Deployment
  Stamps. Ví dụ: Queue-Based Load Leveling cho job tính doanh thu của Olist Shop.
- **Data Management**: Cache-Aside, CQRS, Event Sourcing, Materialized View, Sharding, Saga, Transactional Outbox. Ví dụ: Saga cho đặt
  hàng (giữ tồn kho, authorize thẻ, giữ chỗ vận chuyển, bước bù khi hỏng).
- **Design & Implementation**: Sidecar, Ambassador, Anti-Corruption Layer, Strangler Fig, Backends for Frontends, Gateway Routing. Ví
  dụ: Strangler Fig tách dần monolith qua gateway.
- **Management & Monitoring**: External Configuration Store, Health Endpoint Monitoring, Gateway Offloading. Ví dụ: timeout, số retry,
  cờ tính năng ở một store chung để đổi trong sự cố không cần deploy.

Câu tiếp theo hay gặp: "pattern nào bạn đã thấy dùng sai?". Ví dụ tốt: CQRS cho CRUD đơn giản (thêm độ trễ đồng bộ mà không được gì),
Cache-Aside không TTL, retry ở mọi tầng.

## Thiết kế: trang sản phẩm của Olist Shop gọi một dịch vụ gợi ý sản phẩm chậm và thỉnh thoảng hỏng. Bạn thiết kế thế nào?

- Xác định phần nào là cốt lõi: trang sản phẩm phải hiện giá, tồn kho, nút mua; khối gợi ý là phần thêm. Thiết kế để gợi ý hỏng thì trang
  vẫn hiện (graceful degradation).
- Timeout ngắn theo p99 thật (ví dụ 200 ms) cho lời gọi gợi ý, trong pool riêng (Bulkhead) để nó không chiếm thread, kết nối của phần
  cốt lõi.
- Circuit breaker: khi dịch vụ hỏng liên tục thì không gọi nữa, trả fallback: danh sách bán chạy theo danh mục, tính sẵn mỗi giờ
  (Materialized View) và cache (Cache-Aside).
- Retry: tối đa một lần, chỉ ở một tầng, có jitter; hay không retry, vì fallback đã đủ tốt và người dùng không chờ.
- Có thể tải khối gợi ý bất đồng bộ từ trình duyệt sau khi trang chính đã hiện, để độ trễ của nó không cộng vào trang.
- Quan sát: tỉ lệ fallback, trạng thái breaker, p99 của dịch vụ gợi ý; alert theo SLO của trang sản phẩm, không theo từng lỗi lẻ của
  gợi ý.
- Đánh đổi nói rõ với nghiệp vụ: fallback làm gợi ý kém cá nhân hoá hơn, đổi lại trang không bao giờ chết vì nó.
