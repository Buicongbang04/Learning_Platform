# Lời giải: đưa Olist Shop vào mesh Linkerd, mTLS và chỉ API, worker được gọi Redis

## Cách làm

1. `olist-shop.yaml`: thêm ServiceAccount `api`, `worker`; mỗi pod template có `annotations: {linkerd.io/inject: enabled}` và
   `serviceAccountName` tương ứng. Proxy injector (webhook của Linkerd) thấy annotation khi pod được tạo, thêm init container
   `linkerd-network-validator` và native sidecar `linkerd-proxy`. linkerd-cni đã đặt luật chuyển hướng trong network namespace của pod,
   nên pod không cần NET_ADMIN và vẫn chạy dưới Pod Security baseline.
2. Khi khởi động, proxy gửi token ServiceAccount (volume projected riêng của Linkerd, không phải token tự mount của pod) tới
   `linkerd-identity` để xin chứng chỉ có tên `<sa>.<ns>.serviceaccount.identity.linkerd.cluster.local`, hạn 24 giờ, tự xoay. Đó là
   lý do `automountServiceAccountToken: false` vẫn chạy.
3. `redis-policy.yaml`: `Server` gom cổng `redis` của pod Redis; `proxyProtocol: opaque` vì Redis không phải HTTP (6379 cũng nằm trong
   danh sách cổng opaque mặc định của Linkerd, ghi rõ vẫn tốt hơn). `MeshTLSAuthentication` bằng `identityRefs` hai ServiceAccount
   nên không phải ghi tên namespace. `AuthorizationPolicy` nối hai thứ.

## Vì sao chấm như vậy

- Có Server mà chưa có AuthorizationPolicy thì mọi kết nối tới cổng đó bị từ chối: chính `api` cũng mất Redis, `/readyz` báo
  `"redis":"error"`. Test `/readyz` và job của worker bắt lỗi này.
- `legacy-report` không có proxy nên không có chứng chỉ; proxy của Redis thấy kết nối `tls="no_identity"` và từ chối (connection
  reset). `intruder` có mTLS nhưng danh tính không nằm trong danh sách: proxy đóng kết nối ngay.
- Test đối chứng chứng minh trước khi có policy cả hai đều PING được, nên chặn là do policy của bạn chứ không do mạng.
- Danh sách cho phép đúng hai danh tính: dùng `identities: ["*.<ns>..."]` thì intruder lọt.

## So với NetworkPolicy ở module 11

NetworkPolicy chặn theo IP và nhãn pod: ai tạo được pod mang nhãn `app.kubernetes.io/name: api` là qua. Danh tính mTLS gắn với
ServiceAccount, và một pod chỉ dùng được ServiceAccount có trong namespace của nó; muốn giả làm api phải có quyền chạy pod bằng
ServiceAccount `api`. Hai lớp bổ sung cho nhau: NetworkPolicy chặn ở tầng mạng (kể cả traffic đi vòng proxy), mesh xác thực danh
tính và mã hoá.

## Lỗi hay gặp

- Đặt annotation ở `metadata` của Deployment: không có tác dụng, injector chỉ đọc annotation của pod (hay của namespace).
- Quên `serviceAccountName`: mọi pod dùng `default`, danh tính trùng nhau, policy không phân biệt được.
- `proxyProtocol: HTTP/1` cho Redis: proxy cố parse HTTP, kết nối hỏng.
- Thêm Server trước khi workload hợp lệ có danh tính: trong lúc rollout, kết nối từ pod cũ (chưa có proxy) bị chặn. Ở production, áp
  policy sau khi mọi client đã vào mesh, và theo dõi `authz_deny` từng bước.
