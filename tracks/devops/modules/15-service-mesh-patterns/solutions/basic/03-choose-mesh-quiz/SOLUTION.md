# Lời giải: trắc nghiệm có cần mesh không, chọn mesh nào, chọn pattern nào

| Câu | Đáp án | Giải thích ngắn |
| --- | --- | --- |
| three-services | b | Ba service, một team, chưa có yêu cầu mTLS: mesh thêm control plane, proxy trong mọi pod, thêm một thứ phải nâng cấp và gỡ lỗi mà chưa giải quyết vấn đề nào đang có. NetworkPolicy, retry trong client và metrics của app đủ. Istio "để sẵn" là chi phí trả trước cho nhu cầu chưa có |
| pci-mtls | c | 25 service, yêu cầu mTLS cho kiểm toán, 2 người platform: Linkerd bật mTLS mặc định, xoay chứng chỉ 24 giờ, danh tính theo ServiceAccount, ít thứ cấu hình. Sửa code từng service tốn công nhiều quý; TLS ở ingress không bảo vệ traffic bên trong; NetworkPolicy không mã hoá |
| vm-and-k8s | b | Consul service mesh chạy trên VM, Nomad lẫn Kubernetes, dùng Vault làm CA. Linkerd và Cilium tập trung vào Kubernetes; CoreDNS không cho mTLS |
| rich-traffic | a | Định tuyến theo header, fault injection, rate limit toàn cục, mở rộng WebAssembly: Istio (Envoy) mạnh nhất ở L7, và team có người chuyên để gánh độ phức tạp. Linkerd cố ý giữ ít tính năng; kube-proxy không làm L7 |
| sidecar-cost | d | Ambient (Istio) tách L4 (ztunnel theo node, lo mTLS) khỏi L7 (waypoint chỉ cho namespace cần): RAM không tỉ lệ với số pod, nâng ztunnel không phải restart pod của ứng dụng. Tắt mTLS bỏ mất lý do dùng mesh; RAM của sidecar không phụ thuộc replica của control plane |
| retry-where | c | Hai chặng mỗi chặng 3 lần thử: mỗi lần thử của mobile-bff tới catalog sinh 3 lần thử của catalog tới search, 3 x 3 = 9. Retry chồng tầng nhân lên; đó là cách một sự cố nhỏ thành retry storm. Chỉ retry ở một tầng, có budget |
| payment-retry | b | Timeout không cho biết server đã làm hay chưa. Gửi lại với cùng Idempotency-Key, server tra key và trả kết quả cũ. Không retry thì khách tự bấm lại, vẫn thành hai payment; retry dồn dập là thêm tải; GET không tạo được payment |
| slow-dependency | a | Lỗi lan vì mọi thread dùng chung một pool: Bulkhead cô lập pool cho đối tác, timeout cắt chờ, circuit breaker trả lỗi nhanh khi đối tác hỏng. Cache giúp đọc lặp nhưng lần đầu vẫn treo; Event Sourcing và Strangler Fig không liên quan |
| black-friday-spike | c | Việc không cần xong ngay: Queue-Based Load Leveling đệm đợt tăng, worker xử lý theo tốc độ ổn định. CQRS tách đọc ghi chứ không đệm tải; Health Endpoint Monitoring chỉ phát hiện |
| legacy-migration | b | Strangler Fig: lớp định tuyến (gateway, mesh) đưa từng route sang service mới, monolith co lại dần, không có ngày chuyển đổi lớn. Ambassador là proxy cho lời gọi ra ngoài; Sharding chia dữ liệu |
| mesh-gives | a, b, c, e | Mesh cho mTLS theo danh tính, golden metrics theo cặp service, retry và timeout theo route, chia traffic theo trọng số. Idempotency là việc của ứng dụng và dữ liệu: proxy không biết hai POST là cùng một payment |
| mesh-not-fix | a, b, c | Không ai đọc được proxy khi có sự cố, quá ít service, cluster thiếu RAM: mesh thêm rủi ro nhiều hơn lợi. Yêu cầu mTLS bắt buộc từ kiểm toán là lý do mạnh để dùng mesh, không phải để hoãn |
