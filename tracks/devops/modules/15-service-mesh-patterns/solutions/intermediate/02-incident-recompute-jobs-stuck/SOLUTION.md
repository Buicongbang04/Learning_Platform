# Lời giải: job tính doanh thu không bao giờ xong

## Nguyên nhân

Hai lỗi chồng nhau trong `worker.yaml`, cái nào một mình cũng đủ làm Redis từ chối worker:

1. **`config.linkerd.io/skip-outbound-ports: "6379"`** trên pod template. Annotation này bảo linkerd-cni không chuyển kết nối ra cổng 6379
   qua proxy. Pod vẫn có proxy (2/2), vẫn có chứng chỉ, nhưng kết nối tới Redis đi thẳng, không mTLS. Proxy của Redis thấy kết nối
   `tls="no_identity"`, `no_tls_reason="port_skipped"`, và AuthorizationPolicy của platform chỉ cho danh tính mTLS: từ chối (connection
   reset). Annotation này hay được thêm khi gỡ lỗi (để loại proxy khỏi nghi vấn) rồi bị quên.
2. **ServiceAccount đổi tên thành `olist-worker`** trong đợt chuẩn hoá. Danh tính mTLS của worker thành
   `olist-worker.<ns>.serviceaccount.identity.linkerd.cluster.local`, trong khi `MeshTLSAuthentication` của platform chỉ nêu `api` và
   `worker`. Bỏ (1) thôi thì kết nối đã là mTLS nhưng vẫn bị từ chối, lần này dòng `inbound_tcp_authz_deny_total` có `tls="true"` và
   `client_id="olist-worker..."`, proxy đóng kết nối không lời giải thích (`Connection closed by server`).

Sửa: bỏ annotation `skip-outbound-ports`, đổi ServiceAccount về `worker` (cả object lẫn `serviceAccountName`). Không đụng policy:
thêm `olist-worker` vào MeshTLSAuthentication hay xoá AuthorizationPolicy thì chạy được nhưng là sửa object của team khác, và cách
thứ hai mở Redis cho mọi pod.

## Đường chẩn đoán

1. Log worker: `ConnectionError` tới Redis. api cũng nói chuyện với Redis và ổn, nên Redis sống và mạng tới nó thông: vấn đề nằm ở
   cái gì khác giữa api và worker.
2. Metrics của proxy Redis (`linkerd diagnostics proxy-metrics -n <ns> deploy/redis`):
   - `tcp_open_total{...,tls="true",client_id="api.<ns>..."}` tăng: api vào bằng mTLS.
   - `inbound_tcp_authz_deny_total{...,tls="no_identity",no_tls_reason="port_skipped"}` tăng theo nhịp worker thử lại: có ai đó tới
     Redis không qua proxy của mình.
3. So pod worker với pod api: worker có `config.linkerd.io/skip-outbound-ports: "6379"`. Bỏ, apply.
4. Vẫn lỗi. Metrics Redis giờ có `inbound_tcp_authz_deny_total{...,tls="true",client_id="olist-worker.<ns>..."}`. Đọc
   `platform.yaml`: chỉ `api`, `worker`. Đổi ServiceAccount, apply, `jobs_processed_total` tăng.

Ở bước 2, `mesh_status` của testkit cũng cho thấy `denied` của Redis tăng, còn `mesh_status` của worker vẫn `injected` và `mtls`: đúng
cái bẫy "pod trông như đã vào mesh".

## Vì sao 2/2 chưa đủ

`2/2 Running` chỉ nói pod có proxy. Traffic có đi qua proxy hay không do luật chuyển hướng (CNI hay init container) quyết định, và các
annotation `skip-inbound-ports`, `skip-outbound-ports`, `opaque-ports` đổi luật đó cho từng cổng. Danh tính thì do ServiceAccount quyết
định. Muốn biết chắc, xem metrics hai phía: client có `outbound` tới đích với `tls="true"`, server có `client_id` đúng.

## Phòng ngừa

- CI chạy `kube_manifest_problems` của riêng team (hay conftest/Kyverno): cấm `skip-outbound-ports` trên workload production trừ khi có
  nhãn ngoại lệ được review.
- Đổi ServiceAccount là đổi danh tính: checklist review cho mọi thay đổi `serviceAccountName` nhắc tìm mọi `MeshTLSAuthentication`,
  RoleBinding nêu tên cũ.
- Alert khi `inbound_tcp_authz_deny_total` của Redis tăng liên tục (không phải vài lần lẻ của pod lạ) và khi `jobs_processed_total`
  đứng yên trong khi độ dài `olist:jobs` tăng.

## Rubric tự đánh giá phần giải thích (5 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Tìm được cả hai nguyên nhân, nói được mỗi cái một mình cũng đủ gây lỗi | 2 |
| Dẫn được bằng chứng cụ thể (nhãn `tls`, `no_tls_reason`, `client_id` trong metrics, so sánh với api) | 1 |
| Sửa đúng phạm vi, không nới policy của platform | 1 |
| Đề xuất phòng ngừa kiểm được tự động | 1 |
